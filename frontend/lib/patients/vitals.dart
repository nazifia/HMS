import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

class VitalsScreen extends StatefulWidget {
  const VitalsScreen({super.key, required this.patient});

  final Map<String, dynamic> patient;

  @override
  State<VitalsScreen> createState() => _VitalsScreenState();
}

class _VitalsScreenState extends State<VitalsScreen> {
  int _reloadToken = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Vitals · ${widget.patient['full_name']}')),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final added = await Navigator.of(context).push<bool>(
            MaterialPageRoute(
              builder: (_) => RecordVitalsScreen(patient: widget.patient),
            ),
          );
          if (added == true) setState(() => _reloadToken++);
        },
        child: const Icon(Icons.add),
      ),
      body: PagedList(
        key: ValueKey(_reloadToken),
        path: '/patients/api/vitals/',
        query: {'patient': '${widget.patient['id']}'},
        emptyMessage: 'No vitals recorded',
        itemBuilder: (context, row) => ListTile(
          title: Text(
            [
              if ('${row['blood_pressure']}'.isNotEmpty)
                'BP ${row['blood_pressure']}',
              if (row['pulse_rate'] != null) 'HR ${row['pulse_rate']}',
              if (row['temperature'] != null) '${row['temperature']}°C',
              if (row['oxygen_saturation'] != null)
                'SpO₂ ${row['oxygen_saturation']}%',
            ].join(' · '),
          ),
          subtitle: Text(
            '${row['date_time'].toString().replaceFirst('T', ' ').split('.').first}'
            ' · ${row['recorded_by']}'
            '${row['bmi'] == null ? '' : ' · BMI ${row['bmi']}'}',
          ),
        ),
      ),
    );
  }
}

class RecordVitalsScreen extends StatefulWidget {
  const RecordVitalsScreen({super.key, required this.patient});

  final Map<String, dynamic> patient;

  @override
  State<RecordVitalsScreen> createState() => _RecordVitalsScreenState();
}

class _RecordVitalsScreenState extends State<RecordVitalsScreen> {
  final _fields = {
    'temperature': TextEditingController(),
    'blood_pressure_systolic': TextEditingController(),
    'blood_pressure_diastolic': TextEditingController(),
    'pulse_rate': TextEditingController(),
    'respiratory_rate': TextEditingController(),
    'oxygen_saturation': TextEditingController(),
    'height': TextEditingController(),
    'weight': TextEditingController(),
  };
  final _labels = const {
    'temperature': 'Temperature (°C)',
    'blood_pressure_systolic': 'Systolic BP (mmHg)',
    'blood_pressure_diastolic': 'Diastolic BP (mmHg)',
    'pulse_rate': 'Pulse (bpm)',
    'respiratory_rate': 'Respiratory rate',
    'oxygen_saturation': 'SpO₂ (%)',
    'height': 'Height (cm)',
    'weight': 'Weight (kg)',
  };
  final _notes = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    _notes.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final payload = <String, dynamic>{
      'patient': widget.patient['id'],
      'notes': _notes.text.trim(),
    };
    // Send only what was filled in — a blank field is "not measured", not zero.
    _fields.forEach((name, controller) {
      final value = controller.text.trim();
      if (value.isNotEmpty) payload[name] = value;
    });

    if (payload.length <= 2) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Record at least one measurement')),
      );
      return;
    }

    setState(() => _busy = true);
    try {
      await Api.post('/patients/api/vitals/', payload);
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
      appBar: AppBar(title: const Text('Record vitals')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (final entry in _fields.entries) ...[
            TextField(
              controller: entry.value,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                labelText: _labels[entry.key],
                border: const OutlineInputBorder(),
                isDense: true,
              ),
            ),
            const SizedBox(height: 10),
          ],
          TextField(
            controller: _notes,
            decoration: const InputDecoration(
              labelText: 'Notes',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: const Text('Save vitals'),
          ),
        ],
      ),
    );
  }
}

class MedicalHistoryScreen extends StatefulWidget {
  const MedicalHistoryScreen({super.key, required this.patient});

  final Map<String, dynamic> patient;

  @override
  State<MedicalHistoryScreen> createState() => _MedicalHistoryScreenState();
}

class _MedicalHistoryScreenState extends State<MedicalHistoryScreen> {
  int _reloadToken = 0;

  Future<void> _add() async {
    final diagnosis = TextEditingController();
    final treatment = TextEditingController();
    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add history entry'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: diagnosis,
              autofocus: true,
              decoration: const InputDecoration(labelText: 'Diagnosis'),
            ),
            TextField(
              controller: treatment,
              decoration: const InputDecoration(labelText: 'Treatment'),
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
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (saved != true || diagnosis.text.trim().isEmpty) return;

    try {
      await Api.post('/patients/api/medical-history/', {
        'patient': widget.patient['id'],
        'diagnosis': diagnosis.text.trim(),
        'treatment': treatment.text.trim(),
        'date': DateTime.now().toIso8601String(),
      });
      setState(() => _reloadToken++);
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('History · ${widget.patient['full_name']}')),
      floatingActionButton: FloatingActionButton(
        onPressed: _add,
        child: const Icon(Icons.add),
      ),
      body: PagedList(
        key: ValueKey(_reloadToken),
        path: '/patients/api/medical-history/',
        query: {'patient': '${widget.patient['id']}'},
        emptyMessage: 'No medical history recorded',
        itemBuilder: (context, row) => ListTile(
          title: Text('${row['diagnosis']}'),
          subtitle: Text(
            '${row['treatment']}\n'
            '${row['date'].toString().split('T').first} · ${row['doctor_name']}',
          ),
          isThreeLine: true,
        ),
      ),
    );
  }
}
