import 'package:flutter/material.dart';

import '../api.dart';

/// One value per parameter, plus whether it reads as normal.
class ResultEntryScreen extends StatefulWidget {
  const ResultEntryScreen({
    super.key,
    required this.requestId,
    required this.test,
  });

  final int requestId;
  final Map<String, dynamic> test;

  @override
  State<ResultEntryScreen> createState() => _ResultEntryScreenState();
}

class _ResultEntryScreenState extends State<ResultEntryScreen> {
  late final List<Map<String, dynamic>> _parameters =
      ((widget.test['parameters'] as List?) ?? const [])
          .cast<Map<String, dynamic>>();
  late final Map<int, TextEditingController> _values = {
    for (final p in _parameters) p['id'] as int: TextEditingController(),
  };
  late final Map<int, bool> _normal = {
    for (final p in _parameters) p['id'] as int: true,
  };
  final _notes = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    for (final controller in _values.values) {
      controller.dispose();
    }
    _notes.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final parameters = <String, dynamic>{};
    _values.forEach((id, controller) {
      final value = controller.text.trim();
      // A blank parameter is one that was not measured, not a zero.
      if (value.isNotEmpty) {
        parameters['$id'] = {'value': value, 'is_normal': _normal[id]};
      }
    });

    if (parameters.isEmpty && _notes.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter at least one value')),
      );
      return;
    }

    setState(() => _busy = true);
    try {
      await Api.post(
        '/laboratory/api/requests/${widget.requestId}/enter-result/',
        {
          'test': widget.test['id'],
          'notes': _notes.text.trim(),
          'parameters': parameters,
        },
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
      appBar: AppBar(title: Text('${widget.test['name']}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_parameters.isEmpty)
            const Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: Text(
                'This test has no parameters configured — record the finding '
                'in the notes instead.',
              ),
            ),
          for (final parameter in _parameters) ...[
            TextField(
              controller: _values[parameter['id']],
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                labelText:
                    '${parameter['name']}${parameter['unit'] == null || parameter['unit'].isEmpty ? '' : ' (${parameter['unit']})'}',
                helperText: parameter['normal_range']?.isEmpty ?? true
                    ? null
                    : 'normal ${parameter['normal_range']}',
                border: const OutlineInputBorder(),
                isDense: true,
              ),
            ),
            SwitchListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(
                _normal[parameter['id']] == true
                    ? 'Within normal range'
                    : 'Flagged abnormal',
                style: TextStyle(
                  color: _normal[parameter['id']] == true
                      ? null
                      : Theme.of(context).colorScheme.error,
                ),
              ),
              value: _normal[parameter['id']] ?? true,
              onChanged: (on) =>
                  setState(() => _normal[parameter['id'] as int] = on),
            ),
            const SizedBox(height: 8),
          ],
          TextField(
            controller: _notes,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Notes',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: const Text('Save result'),
          ),
        ],
      ),
    );
  }
}
