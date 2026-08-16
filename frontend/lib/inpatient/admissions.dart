import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';
import 'ward_round.dart';

/// Current inpatients, with the ward round and the discharge behind each one.
class AdmissionListScreen extends StatefulWidget {
  const AdmissionListScreen({super.key});

  @override
  State<AdmissionListScreen> createState() => _AdmissionListScreenState();
}

class _AdmissionListScreenState extends State<AdmissionListScreen> {
  String _status = 'admitted';
  String _search = '';
  int _reloadToken = 0;

  static const _statuses = {
    'admitted': 'On the ward',
    'discharged': 'Discharged',
    'all': 'All',
  };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Admissions')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Patient name, ID or diagnosis',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onSubmitted: (v) => setState(() => _search = v.trim()),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                for (final entry in _statuses.entries)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: FilterChip(
                      label: Text(entry.value),
                      selected: _status == entry.key,
                      onSelected: (_) => setState(() => _status = entry.key),
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: PagedList(
              key: ValueKey('$_status$_search$_reloadToken'),
              path: '/inpatient/api/admissions/',
              query: {'status': _status, 'search': _search},
              emptyMessage: 'No admissions',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['patient_name']} (${row['patient_number']})'),
                subtitle: Text(
                  '${row['ward_name']} bed ${row['bed_number']}\n'
                  '${row['diagnosis']} · day ${row['duration_days']}',
                ),
                isThreeLine: true,
                trailing: row['is_active'] == true
                    ? null
                    : Text('${row['status_display']}'),
                onTap: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) =>
                          AdmissionScreen(admissionId: row['id'] as int),
                    ),
                  );
                  setState(() => _reloadToken++);
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// One admission: where the patient is, what it has cost, and what the ward
/// can do next.
class AdmissionScreen extends StatefulWidget {
  const AdmissionScreen({super.key, required this.admissionId});

  final int admissionId;

  @override
  State<AdmissionScreen> createState() => _AdmissionScreenState();
}

class _AdmissionScreenState extends State<AdmissionScreen> {
  Map<String, dynamic>? _admission;
  Map<String, dynamic>? _charges;
  String? _error;
  bool _busy = false;

  String get _base => '/inpatient/api/admissions/${widget.admissionId}';

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    try {
      final admission = await Api.get('$_base/');
      final charges = await Api.get('$_base/charges/');
      if (!mounted) return;
      setState(() {
        _admission = admission as Map<String, dynamic>;
        _charges = charges as Map<String, dynamic>;
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _act(Future<dynamic> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
      await _reload();
    }
  }

  Future<void> _discharge() async {
    final notes = TextEditingController();
    var status = 'discharged';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Discharge patient'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: status,
                decoration: const InputDecoration(labelText: 'Outcome'),
                items: const [
                  DropdownMenuItem(value: 'discharged', child: Text('Discharged')),
                  DropdownMenuItem(value: 'transferred', child: Text('Transferred out')),
                  DropdownMenuItem(value: 'deceased', child: Text('Deceased')),
                ],
                onChanged: (v) => setDialogState(() => status = v ?? status),
              ),
              TextField(
                controller: notes,
                decoration: const InputDecoration(labelText: 'Discharge notes'),
                maxLines: 3,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Discharge'),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true) return;
    await _act(() => Api.post('$_base/discharge/', {
          'status': status,
          'discharge_notes': notes.text.trim(),
        }));
  }

  Future<void> _transfer() async {
    final bed = await Navigator.of(context).push<Map<String, dynamic>>(
      MaterialPageRoute(builder: (_) => const _FreeBedPickerScreen()),
    );
    if (bed == null) return;
    await _act(() => Api.post('$_base/transfer/', {'bed': bed['id']}));
  }

  @override
  Widget build(BuildContext context) {
    final admission = _admission;
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Admission')),
        body: Center(child: Text(_error!)),
      );
    }
    if (admission == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final active = admission['is_active'] == true;
    final charges = _charges ?? const {};

    return Scaffold(
      appBar: AppBar(
        title: Text('${admission['patient_name']}'),
        bottom: _busy
            ? const PreferredSize(
                preferredSize: Size.fromHeight(2),
                child: LinearProgressIndicator(),
              )
            : null,
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: ListView(
          children: [
            ListTile(
              leading: const Icon(Icons.bed),
              title: Text(
                '${admission['ward_name']} · bed ${admission['bed_number']}',
              ),
              subtitle: Text(
                '${admission['status_display']} · day ${admission['duration_days']}\n'
                'Admitted ${admission['admission_date'].toString().split('T').first}'
                ' under ${admission['doctor_name']}',
              ),
              isThreeLine: true,
            ),
            ListTile(
              leading: const Icon(Icons.medical_information_outlined),
              title: Text('${admission['diagnosis']}'),
              subtitle: Text('${admission['reason_for_admission']}'),
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.account_balance_wallet_outlined),
              title: Text(
                'Billed ₦${charges['billed'] ?? '—'} · '
                'paid ₦${charges['paid'] ?? '—'}',
              ),
              subtitle: Text(
                'Outstanding ₦${charges['outstanding'] ?? '—'} · '
                'wallet ₦${charges['wallet_balance'] ?? '—'}\n'
                '₦${charges['daily_charge'] ?? '—'} per day',
              ),
              isThreeLine: true,
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.assignment_outlined),
              title: const Text('Ward rounds and nursing notes'),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => WardRoundScreen(admission: admission),
                ),
              ),
            ),
            if (active)
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: FilledButton.tonal(
                        onPressed: _busy ? null : _transfer,
                        child: const Text('Transfer'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: FilledButton(
                        onPressed: _busy ? null : _discharge,
                        child: const Text('Discharge'),
                      ),
                    ),
                  ],
                ),
              ),
            if (!active && admission['discharge_notes'] != null)
              ListTile(
                leading: const Icon(Icons.sticky_note_2_outlined),
                title: Text('${admission['discharge_notes']}'),
              ),
          ],
        ),
      ),
    );
  }
}

/// Pick a free bed anywhere in the hospital — the server refuses anything else.
class _FreeBedPickerScreen extends StatelessWidget {
  const _FreeBedPickerScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Move to bed')),
      body: PagedList(
        path: '/inpatient/api/beds/',
        query: const {'free': 'true'},
        emptyMessage: 'No free beds',
        itemBuilder: (context, row) => ListTile(
          leading: const Icon(Icons.bed_outlined),
          title: Text('${row['ward_name']} · bed ${row['bed_number']}'),
          onTap: () => Navigator.pop(context, row),
        ),
      ),
    );
  }
}
