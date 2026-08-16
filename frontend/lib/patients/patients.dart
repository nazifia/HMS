import 'package:flutter/material.dart';

import '../api.dart';
import '../page_screen.dart';
import '../paged_list.dart';
import 'vitals.dart';
import 'wallet.dart';

const _patientTypes = {
  '': 'All',
  'regular': 'Regular',
  'nhia': 'NHIA',
  'private': 'Private',
  'retainership': 'Retainership',
  'staff': 'Staff',
};

class PatientListScreen extends StatefulWidget {
  /// [picking] turns the list into a chooser: tapping a patient pops it back
  /// to the caller instead of opening their record.
  const PatientListScreen({super.key, this.picking = false});

  final bool picking;

  @override
  State<PatientListScreen> createState() => _PatientListScreenState();
}

class _PatientListScreenState extends State<PatientListScreen> {
  String _search = '';
  String _type = '';
  int _reloadToken = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.picking ? 'Choose patient' : 'Patients'),
      ),
      floatingActionButton: widget.picking
          ? null
          : FloatingActionButton(
              onPressed: () async {
                final created = await Navigator.of(context).push<bool>(
                  MaterialPageRoute(
                    builder: (_) => const RegisterPatientScreen(),
                  ),
                );
                if (created == true) setState(() => _reloadToken++);
              },
              child: const Icon(Icons.person_add),
            ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Name, patient ID or phone',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onSubmitted: (v) => setState(() => _search = v.trim()),
            ),
          ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                for (final entry in _patientTypes.entries)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: FilterChip(
                      label: Text(entry.value),
                      selected: _type == entry.key,
                      onSelected: (_) => setState(() => _type = entry.key),
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: PagedList(
              key: ValueKey('$_search$_type$_reloadToken'),
              path: '/patients/api/patients/',
              query: {'search': _search, 'patient_type': _type},
              emptyMessage: 'No patients match',
              itemBuilder: (context, row) => ListTile(
                leading: CircleAvatar(
                  child: Text('${row['first_name']}'.characters.first),
                ),
                title: Text('${row['full_name']} (${row['patient_id']})'),
                subtitle: Text(
                  '${row['age'] ?? '?'}y · ${row['gender_display']} · '
                  '${row['patient_type_display']}'
                  '${row['phone_number'] == null ? '' : ' · ${row['phone_number']}'}',
                ),
                trailing: row['wallet_balance'] == null
                    ? null
                    : Text('₦${row['wallet_balance']}'),
                onTap: () => widget.picking
                    ? Navigator.pop(context, row)
                    : Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => PatientScreen(patient: row),
                        ),
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class PatientScreen extends StatefulWidget {
  const PatientScreen({super.key, required this.patient});

  final Map<String, dynamic> patient;

  @override
  State<PatientScreen> createState() => _PatientScreenState();
}

class _PatientScreenState extends State<PatientScreen> {
  late Map<String, dynamic> _patient = widget.patient;

  Future<void> _reload() async {
    try {
      final fresh = await Api.get('/patients/api/patients/${_patient['id']}/');
      if (mounted) setState(() => _patient = fresh as Map<String, dynamic>);
    } catch (_) {
      // Keep showing what we already have.
    }
  }

  @override
  Widget build(BuildContext context) {
    final patient = _patient;
    final id = patient['id'] as int;

    return Scaffold(
      appBar: AppBar(
        title: Text('${patient['full_name']}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.open_in_new),
            tooltip: 'Open server page',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => PageScreen(
                  title: 'Patient',
                  path: '/patients/$id/',
                ),
              ),
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: ListView(
          children: [
            ListTile(
              title: Text('${patient['patient_id']}'),
              subtitle: Text(
                '${patient['age'] ?? '?'} years · ${patient['gender_display']} · '
                '${patient['patient_type_display']}'
                '${patient['blood_group'] == null ? '' : ' · ${patient['blood_group']}'}',
              ),
            ),
            ListTile(
              leading: const Icon(Icons.account_balance_wallet_outlined),
              title: const Text('Wallet'),
              trailing: Text('₦${patient['wallet_balance'] ?? '0.00'}'),
              onTap: () async {
                await Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => WalletScreen(patient: patient),
                  ),
                );
                _reload();
              },
            ),
            ListTile(
              leading: const Icon(Icons.monitor_heart_outlined),
              title: const Text('Vitals'),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => VitalsScreen(patient: patient),
                ),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.history_edu_outlined),
              title: const Text('Medical history'),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => MedicalHistoryScreen(patient: patient),
                ),
              ),
            ),
            const Divider(),
            _field('Phone', patient['phone_number']),
            _field('Email', patient['email']),
            _field(
              'Address',
              [patient['address'], patient['city'], patient['state']]
                  .where((v) => v != null && '$v'.isNotEmpty)
                  .join(', '),
            ),
            _field('Occupation', patient['occupation']),
            _field('Primary doctor', patient['primary_doctor_name']),
            _field('Insurance', patient['insurance_provider']),
            const Divider(),
            _field('Allergies', patient['allergies'], warn: true),
            _field('Chronic diseases', patient['chronic_diseases']),
            _field('Current medications', patient['current_medications']),
            _field('Emergency contact', [
              patient['emergency_contact_name'],
              patient['emergency_contact_relation'],
              patient['emergency_contact_phone'],
            ].where((v) => v != null && '$v'.isNotEmpty).join(' · ')),
            _field('Notes', patient['notes']),
          ],
        ),
      ),
    );
  }

  Widget _field(String label, Object? value, {bool warn = false}) {
    if (value == null || '$value'.isEmpty) return const SizedBox.shrink();
    return ListTile(
      dense: true,
      title: Text(label, style: Theme.of(context).textTheme.bodySmall),
      subtitle: Text(
        '$value',
        style: TextStyle(
          color: warn ? Theme.of(context).colorScheme.error : null,
          fontWeight: warn ? FontWeight.bold : null,
        ),
      ),
    );
  }
}

class RegisterPatientScreen extends StatefulWidget {
  const RegisterPatientScreen({super.key});

  @override
  State<RegisterPatientScreen> createState() => _RegisterPatientScreenState();
}

class _RegisterPatientScreenState extends State<RegisterPatientScreen> {
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _phone = TextEditingController();
  final _address = TextEditingController();
  final _city = TextEditingController();
  final _state = TextEditingController();
  String _gender = 'M';
  String _type = 'regular';
  DateTime? _dateOfBirth;
  bool _busy = false;

  Future<void> _submit() async {
    if (_firstName.text.trim().isEmpty ||
        _lastName.text.trim().isEmpty ||
        _dateOfBirth == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Name and date of birth are required')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final patient = await Api.post('/patients/api/patients/', {
        'first_name': _firstName.text.trim(),
        'last_name': _lastName.text.trim(),
        'date_of_birth': _dateOfBirth!.toIso8601String().split('T').first,
        'gender': _gender,
        'patient_type': _type,
        'phone_number': _phone.text.trim(),
        'address': _address.text.trim(),
        'city': _city.text.trim(),
        'state': _state.text.trim(),
      });
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Registered ${patient['patient_id']}')),
      );
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Register patient')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            controller: _firstName,
            decoration: const InputDecoration(
              labelText: 'First name',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _lastName,
            decoration: const InputDecoration(
              labelText: 'Last name',
              border: OutlineInputBorder(),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.cake_outlined),
            title: Text(_dateOfBirth == null
                ? 'Date of birth'
                : _dateOfBirth!.toIso8601String().split('T').first),
            onTap: () async {
              final picked = await showDatePicker(
                context: context,
                initialDate: DateTime(1990),
                firstDate: DateTime(1900),
                lastDate: DateTime.now(),
              );
              if (picked != null) setState(() => _dateOfBirth = picked);
            },
          ),
          DropdownButtonFormField<String>(
            initialValue: _gender,
            decoration: const InputDecoration(labelText: 'Gender'),
            items: const [
              DropdownMenuItem(value: 'M', child: Text('Male')),
              DropdownMenuItem(value: 'F', child: Text('Female')),
              DropdownMenuItem(value: 'O', child: Text('Other')),
            ],
            onChanged: (v) => setState(() => _gender = v ?? 'M'),
          ),
          DropdownButtonFormField<String>(
            initialValue: _type,
            decoration: const InputDecoration(labelText: 'Patient type'),
            items: [
              for (final entry in _patientTypes.entries)
                if (entry.key.isNotEmpty)
                  DropdownMenuItem(value: entry.key, child: Text(entry.value)),
            ],
            onChanged: (v) => setState(() => _type = v ?? 'regular'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _phone,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(
              labelText: 'Phone',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _address,
            decoration: const InputDecoration(
              labelText: 'Address',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _city,
            decoration: const InputDecoration(
              labelText: 'City',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _state,
            decoration: const InputDecoration(
              labelText: 'State',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: const Text('Register'),
          ),
        ],
      ),
    );
  }
}
