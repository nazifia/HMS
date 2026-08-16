import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

/// Rounds and nursing notes against one admission, built for a phone held at
/// the bedside.
class WardRoundScreen extends StatefulWidget {
  const WardRoundScreen({super.key, required this.admission});

  final Map<String, dynamic> admission;

  @override
  State<WardRoundScreen> createState() => _WardRoundScreenState();
}

class _WardRoundScreenState extends State<WardRoundScreen> {
  int _reloadToken = 0;

  int get _admissionId => widget.admission['id'] as int;

  Future<void> _add(bool round) async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => _EntryScreen(admissionId: _admissionId, round: round),
      ),
    );
    if (saved == true) setState(() => _reloadToken++);
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text('${widget.admission['patient_name']}'),
          bottom: const TabBar(tabs: [
            Tab(text: 'Rounds'),
            Tab(text: 'Nursing notes'),
          ]),
        ),
        body: TabBarView(
          children: [
            PagedList(
              key: ValueKey('rounds$_reloadToken'),
              path: '/inpatient/api/rounds/',
              query: {'admission': '$_admissionId'},
              emptyMessage: 'No rounds recorded',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['notes']}'),
                subtitle: Text(
                  [
                    '${row['date_time'].toString().replaceFirst('T', ' ').split('.').first}'
                        ' · ${row['doctor_name']}',
                    if ('${row['treatment_instructions'] ?? ''}'.isNotEmpty)
                      'Treatment: ${row['treatment_instructions']}',
                    if ('${row['medication_instructions'] ?? ''}'.isNotEmpty)
                      'Medication: ${row['medication_instructions']}',
                    if ('${row['diet_instructions'] ?? ''}'.isNotEmpty)
                      'Diet: ${row['diet_instructions']}',
                  ].join('\n'),
                ),
                isThreeLine: true,
              ),
            ),
            PagedList(
              key: ValueKey('notes$_reloadToken'),
              path: '/inpatient/api/nursing-notes/',
              query: {'admission': '$_admissionId'},
              emptyMessage: 'No nursing notes',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['notes']}'),
                subtitle: Text(
                  [
                    '${row['date_time'].toString().replaceFirst('T', ' ').split('.').first}'
                        ' · ${row['nurse_name']}',
                    if ('${row['vital_signs'] ?? ''}'.isNotEmpty)
                      'Vitals: ${row['vital_signs']}',
                    if ('${row['medication_given'] ?? ''}'.isNotEmpty)
                      'Given: ${row['medication_given']}',
                  ].join('\n'),
                ),
                isThreeLine: true,
              ),
            ),
          ],
        ),
        floatingActionButton: Builder(
          builder: (context) => FloatingActionButton(
            onPressed: () =>
                _add(DefaultTabController.of(context).index == 0),
            child: const Icon(Icons.add),
          ),
        ),
      ),
    );
  }
}

class _EntryScreen extends StatefulWidget {
  const _EntryScreen({required this.admissionId, required this.round});

  final int admissionId;
  final bool round;

  @override
  State<_EntryScreen> createState() => _EntryScreenState();
}

class _EntryScreenState extends State<_EntryScreen> {
  final _fields = <String, TextEditingController>{};
  bool _busy = false;

  Map<String, String> get _labels => widget.round
      ? const {
          'notes': 'Round notes',
          'treatment_instructions': 'Treatment instructions',
          'medication_instructions': 'Medication instructions',
          'diet_instructions': 'Diet instructions',
        }
      : const {
          'notes': 'Nursing notes',
          'vital_signs': 'Vital signs',
          'medication_given': 'Medication given',
        };

  @override
  void initState() {
    super.initState();
    for (final name in _labels.keys) {
      _fields[name] = TextEditingController();
    }
  }

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    final payload = <String, dynamic>{'admission': widget.admissionId};
    // Blank means "not recorded" — send only what was written.
    _fields.forEach((name, controller) {
      final value = controller.text.trim();
      if (value.isNotEmpty) payload[name] = value;
    });

    if (payload['notes'] == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Notes are required')),
      );
      return;
    }

    setState(() => _busy = true);
    try {
      await Api.post(
        widget.round
            ? '/inpatient/api/rounds/'
            : '/inpatient/api/nursing-notes/',
        payload,
      );
      if (mounted) Navigator.pop(context, true);
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
      appBar: AppBar(
        title: Text(widget.round ? 'Ward round' : 'Nursing note'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (final entry in _labels.entries) ...[
            TextField(
              controller: _fields[entry.key],
              maxLines: entry.key == 'notes' ? 4 : 2,
              decoration: InputDecoration(
                labelText: entry.value,
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
          ],
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }
}
