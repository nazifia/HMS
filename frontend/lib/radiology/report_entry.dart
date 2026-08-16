import 'package:flutter/material.dart';

import '../api.dart';

const _contrastOptions = {
  'none': 'No contrast',
  'oral': 'Oral',
  'iv': 'IV',
  'both': 'Oral + IV',
  'other': 'Other',
};

const _qualityOptions = {
  'excellent': 'Excellent',
  'good': 'Good',
  'adequate': 'Adequate',
  'poor': 'Poor',
  'non_diagnostic': 'Non-diagnostic',
};

/// Write or correct the report for one order.
///
/// ponytail: text only — attaching a study from the phone needs an image
/// picker plugin and the platform permissions that go with it. `Api.postMultipart`
/// and the server both accept uploads already, so that is a plugin away.
class ReportEntryScreen extends StatefulWidget {
  const ReportEntryScreen({
    super.key,
    required this.orderId,
    required this.order,
    this.result,
  });

  final int orderId;
  final Map<String, dynamic> order;
  final Map<String, dynamic>? result;

  @override
  State<ReportEntryScreen> createState() => _ReportEntryScreenState();
}

class _ReportEntryScreenState extends State<ReportEntryScreen> {
  final _fields = <String, TextEditingController>{};
  final _labels = const {
    'findings': 'Findings',
    'impression': 'Impression',
    'technique': 'Technique',
    'recommendations': 'Recommendations',
    'notes': 'Notes',
  };
  String _contrast = 'none';
  String _quality = 'good';
  bool _abnormal = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final result = widget.result;
    for (final name in _labels.keys) {
      _fields[name] = TextEditingController(
        text: '${result?[name] ?? ''}',
      );
    }
    if (result != null) {
      _contrast = '${result['contrast_used'] ?? 'none'}';
      _quality = '${result['image_quality'] ?? 'good'}';
      _abnormal = result['is_abnormal'] == true;
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
    final payload = <String, dynamic>{
      'contrast_used': _contrast,
      'image_quality': _quality,
      'is_abnormal': _abnormal,
    };
    // Blank means "not recorded" — send only what was written.
    _fields.forEach((name, controller) {
      final value = controller.text.trim();
      if (value.isNotEmpty) payload[name] = value;
    });

    setState(() => _busy = true);
    try {
      await Api.post(
        '/radiology/api/orders/${widget.orderId}/enter-result/',
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
      appBar: AppBar(title: Text('${widget.order['test_name']}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            '${widget.order['patient_name']} (${widget.order['patient_number']})',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 16),
          for (final entry in _labels.entries) ...[
            TextField(
              controller: _fields[entry.key],
              maxLines: entry.key == 'findings' ? 6 : 3,
              decoration: InputDecoration(
                labelText: entry.value,
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
          ],
          DropdownButtonFormField<String>(
            initialValue: _contrast,
            decoration: const InputDecoration(
              labelText: 'Contrast',
              border: OutlineInputBorder(),
            ),
            items: [
              for (final entry in _contrastOptions.entries)
                DropdownMenuItem(value: entry.key, child: Text(entry.value)),
            ],
            onChanged: (v) => setState(() => _contrast = v ?? _contrast),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _quality,
            decoration: const InputDecoration(
              labelText: 'Image quality',
              border: OutlineInputBorder(),
            ),
            items: [
              for (final entry in _qualityOptions.entries)
                DropdownMenuItem(value: entry.key, child: Text(entry.value)),
            ],
            onChanged: (v) => setState(() => _quality = v ?? _quality),
          ),
          SwitchListTile(
            value: _abnormal,
            onChanged: (v) => setState(() => _abnormal = v),
            title: const Text('Abnormal study'),
            contentPadding: EdgeInsets.zero,
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: const Text('Save report'),
          ),
        ],
      ),
    );
  }
}
