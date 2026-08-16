import 'package:flutter/material.dart';

import '../api.dart';

/// Book an appointment: pick patient, doctor and date, then choose from the
/// slots the server says are actually free.
class BookAppointmentScreen extends StatefulWidget {
  const BookAppointmentScreen({super.key});

  @override
  State<BookAppointmentScreen> createState() => _BookAppointmentScreenState();
}

class _BookAppointmentScreenState extends State<BookAppointmentScreen> {
  Map<String, dynamic>? _patient;
  Map<String, dynamic>? _doctor;
  DateTime _date = DateTime.now().add(const Duration(days: 1));
  List<Map<String, dynamic>> _slots = [];
  String _slotMessage = '';
  String? _slot;
  bool _loadingSlots = false;
  bool _busy = false;

  final _reason = TextEditingController();
  final _authorizationCode = TextEditingController();
  String _priority = 'normal';

  @override
  void dispose() {
    _reason.dispose();
    _authorizationCode.dispose();
    super.dispose();
  }

  Future<Map<String, dynamic>?> _search(
    String title,
    String path,
    String Function(Map<String, dynamic>) label,
  ) async {
    final controller = TextEditingController();
    final query = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Search'),
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Search'),
          ),
        ],
      ),
    );
    if (query == null || query.isEmpty) return null;

    final data = await Api.get(path, {'search': query});
    final results = ((data is Map ? data['results'] : data) as List)
        .cast<Map<String, dynamic>>();
    if (!mounted || results.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No matches for "$query"')),
        );
      }
      return null;
    }
    return showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => SimpleDialog(
        title: Text('Matches for "$query"'),
        children: [
          for (final row in results)
            SimpleDialogOption(
              onPressed: () => Navigator.pop(context, row),
              child: Text(label(row)),
            ),
        ],
      ),
    );
  }

  /// Doctors are a short list, so show them all and filter as you type rather
  /// than making the user guess a search term first.
  Future<Map<String, dynamic>?> _pickDoctor() async {
    List<Map<String, dynamic>> doctors;
    try {
      doctors = (await Api.get('/api/accounts/staff/', {'role': 'doctor'}) as List)
          .cast<Map<String, dynamic>>();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
      return null;
    }
    if (!mounted) return null;
    if (doctors.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No doctors are set up yet')),
      );
      return null;
    }

    final filter = TextEditingController();
    return showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) {
          final needle = filter.text.trim().toLowerCase();
          final shown = doctors
              .where((d) => '${d['full_name']}'.toLowerCase().contains(needle))
              .toList();
          return AlertDialog(
            title: const Text('Choose a doctor'),
            content: SizedBox(
              width: double.maxFinite,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: filter,
                    autofocus: true,
                    decoration: const InputDecoration(labelText: 'Filter'),
                    onChanged: (_) => setLocal(() {}),
                  ),
                  const SizedBox(height: 8),
                  Flexible(
                    child: ListView(
                      shrinkWrap: true,
                      children: [
                        for (final doctor in shown)
                          ListTile(
                            title: Text('${doctor['full_name']}'),
                            subtitle: '${doctor['department']}'.isEmpty
                                ? null
                                : Text('${doctor['department']}'),
                            onTap: () => Navigator.pop(context, doctor),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Future<void> _loadSlots() async {
    if (_doctor == null) return;
    setState(() {
      _loadingSlots = true;
      _slot = null;
      _slots = [];
      _slotMessage = '';
    });
    try {
      final body = await Api.get('/appointments/api/appointments/slots/', {
        'doctor': '${_doctor!['id']}',
        'date': _date.toIso8601String().split('T').first,
      });
      setState(() {
        _slots = (body['slots'] as List).cast<Map<String, dynamic>>();
        _slotMessage = '${body['message'] ?? ''}';
      });
    } on ApiException catch (e) {
      setState(() => _slotMessage = e.message);
    } finally {
      if (mounted) setState(() => _loadingSlots = false);
    }
  }

  Future<void> _submit() async {
    if (_patient == null || _doctor == null || _slot == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pick a patient, doctor and time')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final date = _date.toIso8601String().split('T').first;
      await Api.post('/appointments/api/appointments/', {
        'patient': _patient!['id'],
        'doctor': _doctor!['id'],
        // Local wall-clock time; the server attaches the timezone.
        'appointment_date': '${date}T$_slot:00',
        'reason': _reason.text.trim().isEmpty ? 'Consultation' : _reason.text.trim(),
        'priority': _priority,
        'authorization_code': _authorizationCode.text.trim(),
      });
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
        // The slot may have just been taken; refresh what is left.
        _loadSlots();
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isNhia = _patient?['patient_type'] == 'nhia';

    return Scaffold(
      appBar: AppBar(title: const Text('Book appointment')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ListTile(
            leading: const Icon(Icons.person_outline),
            title: Text(_patient == null
                ? 'Patient'
                : '${_patient!['full_name']} (${_patient!['patient_id']})'),
            onTap: () async {
              final chosen = await _search(
                'Find patient',
                '/patients/api/patients/',
                (row) => '${row['full_name']} (${row['patient_id']})',
              );
              if (chosen != null) setState(() => _patient = chosen);
            },
          ),
          ListTile(
            leading: const Icon(Icons.medical_information_outlined),
            title: Text(_doctor == null ? 'Doctor' : '${_doctor!['full_name']}'),
            subtitle: _doctor?['department']?.isNotEmpty ?? false
                ? Text('${_doctor!['department']}')
                : null,
            onTap: () async {
              final chosen = await _pickDoctor();
              if (chosen != null) {
                setState(() => _doctor = chosen);
                _loadSlots();
              }
            },
          ),
          ListTile(
            leading: const Icon(Icons.event_outlined),
            title: Text(_date.toIso8601String().split('T').first),
            onTap: () async {
              final picked = await showDatePicker(
                context: context,
                initialDate: _date,
                firstDate: DateTime.now(),
                lastDate: DateTime.now().add(const Duration(days: 365)),
              );
              if (picked != null) {
                setState(() => _date = picked);
                _loadSlots();
              }
            },
          ),
          const Divider(),
          if (_loadingSlots)
            const Center(child: CircularProgressIndicator())
          else if (_slotMessage.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(
                _slotMessage,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            )
          else if (_doctor == null)
            const Text('Pick a doctor to see free times.')
          else if (_slots.isEmpty)
            const Text('No free slots left on this day.')
          else
            Wrap(
              spacing: 8,
              children: [
                for (final slot in _slots)
                  ChoiceChip(
                    label: Text('${slot['text']}'),
                    selected: _slot == slot['value'],
                    onSelected: (_) =>
                        setState(() => _slot = '${slot['value']}'),
                  ),
              ],
            ),
          const SizedBox(height: 16),
          TextField(
            controller: _reason,
            decoration: const InputDecoration(
              labelText: 'Reason',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _priority,
            decoration: const InputDecoration(labelText: 'Priority'),
            items: const [
              DropdownMenuItem(value: 'normal', child: Text('Normal')),
              DropdownMenuItem(value: 'urgent', child: Text('Urgent')),
              DropdownMenuItem(value: 'emergency', child: Text('Emergency')),
            ],
            onChanged: (v) => setState(() => _priority = v ?? 'normal'),
          ),
          if (isNhia) ...[
            const SizedBox(height: 12),
            TextField(
              controller: _authorizationCode,
              decoration: const InputDecoration(
                labelText: 'NHIA authorization code',
                helperText: 'Required for NHIA patients',
                border: OutlineInputBorder(),
              ),
            ),
          ],
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: const Text('Book'),
          ),
        ],
      ),
    );
  }
}
