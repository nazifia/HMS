import 'package:flutter/material.dart';

import '../api.dart';
import '../patients/patients.dart';

/// One form for eighteen modules: the fields come from
/// `/api/specialty/<kind>/schema/`, so the labels live in the model and cannot
/// go stale here.
class SpecialtyRecordFormScreen extends StatefulWidget {
  const SpecialtyRecordFormScreen({
    super.key,
    required this.kind,
    required this.label,
    this.record,
  });

  final String kind;
  final String label;
  final Map<String, dynamic>? record;

  @override
  State<SpecialtyRecordFormScreen> createState() =>
      _SpecialtyRecordFormScreenState();
}

class _SpecialtyRecordFormScreenState extends State<SpecialtyRecordFormScreen> {
  List<Map<String, dynamic>> _fields = [];
  final _text = <String, TextEditingController>{};
  final _flags = <String, bool>{};
  final _choices = <String, String>{};
  Map<String, dynamic>? _patient;
  bool _loading = true;
  bool _busy = false;
  String? _error;

  bool get _isNew => widget.record == null;

  @override
  void initState() {
    super.initState();
    _loadSchema();
  }

  @override
  void dispose() {
    for (final controller in _text.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _loadSchema() async {
    try {
      final schema = await Api.get('/api/specialty/${widget.kind}/schema/');
      final fields =
          ((schema as Map)['fields'] as List).cast<Map<String, dynamic>>();
      final record = widget.record;
      for (final field in fields) {
        final name = '${field['name']}';
        final value = record?[name];
        switch (field['type']) {
          case 'boolean':
            _flags[name] = value == true;
            break;
          case 'choice':
            _choices[name] = '${value ?? ''}';
            break;
          default:
            _text[name] = TextEditingController(
              text: value == null ? '' : '$value',
            );
        }
      }
      if (!mounted) return;
      setState(() {
        _fields = fields;
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  Future<void> _pickPatient() async {
    final patient = await Navigator.of(context).push<Map<String, dynamic>>(
      MaterialPageRoute(builder: (_) => const PatientListScreen(picking: true)),
    );
    if (patient != null) setState(() => _patient = patient);
  }

  Future<void> _submit() async {
    if (_isNew && _patient == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Choose a patient first')),
      );
      return;
    }

    final payload = <String, dynamic>{
      if (_isNew) 'patient': _patient!['id'],
      ..._flags,
    };
    // Blank means "not recorded" — send only what was filled in.
    _text.forEach((name, controller) {
      final value = controller.text.trim();
      if (value.isNotEmpty) payload[name] = value;
    });
    _choices.forEach((name, value) {
      if (value.isNotEmpty) payload[name] = value;
    });

    setState(() => _busy = true);
    try {
      if (_isNew) {
        await Api.post('/api/specialty/${widget.kind}/records/', payload);
      } else {
        await Api.patch(
          '/api/specialty/${widget.kind}/records/${widget.record!['id']}/',
          payload,
        );
      }
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

  Widget _control(Map<String, dynamic> field) {
    final name = '${field['name']}';
    final label = '${field['label']}';
    final help = '${field['help_text'] ?? ''}';

    switch (field['type']) {
      case 'boolean':
        return SwitchListTile(
          value: _flags[name] ?? false,
          title: Text(label),
          subtitle: help.isEmpty ? null : Text(help),
          contentPadding: EdgeInsets.zero,
          onChanged: (v) => setState(() => _flags[name] = v),
        );
      case 'choice':
        final options =
            (field['choices'] as List).cast<Map<String, dynamic>>();
        final value = _choices[name];
        return DropdownButtonFormField<String>(
          initialValue: options.any((o) => '${o['value']}' == value)
              ? value
              : null,
          isExpanded: true,
          decoration: InputDecoration(
            labelText: label,
            helperText: help.isEmpty ? null : help,
            border: const OutlineInputBorder(),
          ),
          items: [
            for (final option in options)
              DropdownMenuItem(
                value: '${option['value']}',
                child: Text('${option['label']}'),
              ),
          ],
          onChanged: (v) => setState(() => _choices[name] = v ?? ''),
        );
      default:
        final isLong = field['type'] == 'text';
        return TextField(
          controller: _text[name],
          maxLines: isLong ? 3 : 1,
          keyboardType: field['type'] == 'number'
              ? const TextInputType.numberWithOptions(decimal: true)
              : TextInputType.text,
          decoration: InputDecoration(
            labelText: label,
            helperText: help.isEmpty ? null : help,
            border: const OutlineInputBorder(),
          ),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: Text(widget.label)),
        body: Center(child: Text(_error!)),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_isNew ? 'New ${widget.label} record' : widget.label),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_isNew)
            ListTile(
              leading: const Icon(Icons.person_outline),
              title: Text(_patient == null
                  ? 'Choose patient'
                  : '${_patient!['full_name']}'),
              trailing: const Icon(Icons.chevron_right),
              onTap: _pickPatient,
            )
          else
            ListTile(
              leading: const Icon(Icons.person),
              title: Text('${widget.record!['patient_name']}'),
              subtitle: Text('${widget.record!['patient_number']}'),
            ),
          const Divider(),
          for (final field in _fields) ...[
            _control(field),
            const SizedBox(height: 12),
          ],
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: Text(_isNew ? 'Save record' : 'Update record'),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
