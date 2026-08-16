import 'package:flutter/material.dart';

import '../api.dart';

/// The WHO-style safety items, in the order a theatre reads them out.
const _items = {
  'patient_identified': 'Patient identified',
  'site_marked': 'Surgical site marked',
  'consent_confirmed': 'Consent confirmed',
  'allergies_reviewed': 'Allergies reviewed',
  'anesthesia_safety_check_completed': 'Anaesthesia safety check done',
  'surgical_safety_checklist_completed': 'Surgical safety checklist done',
  'imaging_available': 'Imaging available',
  'blood_products_available': 'Blood products available',
  'antibiotics_administered': 'Antibiotics administered',
};

/// A real checklist, ticked at the table — not a text field.
class ChecklistScreen extends StatefulWidget {
  const ChecklistScreen({
    super.key,
    required this.surgeryId,
    required this.surgery,
  });

  final int surgeryId;
  final Map<String, dynamic> surgery;

  @override
  State<ChecklistScreen> createState() => _ChecklistScreenState();
}

class _ChecklistScreenState extends State<ChecklistScreen> {
  final _ticked = <String, bool>{for (final key in _items.keys) key: false};
  final _notes = TextEditingController();
  bool _busy = false;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _notes.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final existing = widget.surgery['pre_op_checklist'] as Map<String, dynamic>?;
    if (existing != null) {
      setState(() {
        for (final key in _items.keys) {
          _ticked[key] = existing[key] == true;
        }
        _notes.text = '${existing['notes'] ?? ''}';
      });
    }
    setState(() => _loading = false);
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await Api.post(
        '/theatre/api/surgeries/${widget.surgeryId}/checklist/',
        {..._ticked, 'notes': _notes.text.trim()},
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
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final outstanding = _ticked.values.where((v) => !v).length;

    return Scaffold(
      appBar: AppBar(title: const Text('Pre-operative checklist')),
      body: ListView(
        children: [
          ListTile(
            title: Text('${widget.surgery['patient_name']}'),
            subtitle: Text(
              '${widget.surgery['surgery_type_name']} · '
              '${widget.surgery['theatre_name']}',
            ),
            trailing: Text(
              outstanding == 0 ? 'Complete' : '$outstanding left',
              style: TextStyle(
                color: outstanding == 0
                    ? Colors.green
                    : Theme.of(context).colorScheme.error,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const Divider(),
          for (final entry in _items.entries)
            CheckboxListTile(
              value: _ticked[entry.key],
              title: Text(entry.value),
              onChanged: _busy
                  ? null
                  : (v) => setState(() => _ticked[entry.key] = v ?? false),
            ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _notes,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Notes',
                border: OutlineInputBorder(),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: FilledButton(
              onPressed: _busy ? null : _save,
              child: const Text('Save checklist'),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
