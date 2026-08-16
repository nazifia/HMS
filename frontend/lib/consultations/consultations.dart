import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';
import 'clerking.dart';
import 'referrals.dart';

const _consultationStatuses = {
  'in_progress': 'Resume',
  'completed': 'Complete',
  'cancelled': 'Cancel',
};

/// The clinic queue and the doctor's own consultations, side by side.
class ClinicScreen extends StatefulWidget {
  const ClinicScreen({super.key});

  @override
  State<ClinicScreen> createState() => _ClinicScreenState();
}

class _ClinicScreenState extends State<ClinicScreen> {
  int _reloadToken = 0;
  bool _mineOnly = false;

  Future<void> _callIn(int entryId) async {
    try {
      final result =
          await Api.post('/consultations/api/waiting-list/$entryId/call-in/');
      if (!mounted) return;
      setState(() => _reloadToken++);
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => ConsultationScreen(
            consultation: result['consultation'] as Map<String, dynamic>,
          ),
        ),
      );
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
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Clinic'),
          bottom: const TabBar(tabs: [
            Tab(text: 'Queue'),
            Tab(text: 'Consultations'),
            Tab(text: 'Referrals'),
          ]),
          actions: [
            IconButton(
              icon: Icon(_mineOnly ? Icons.person : Icons.people_outline),
              tooltip: _mineOnly ? 'Showing mine' : 'Showing everyone',
              onPressed: () => setState(() {
                _mineOnly = !_mineOnly;
                _reloadToken++;
              }),
            ),
          ],
        ),
        body: TabBarView(
          children: [
            PagedList(
              key: ValueKey('queue$_mineOnly$_reloadToken'),
              path: '/consultations/api/waiting-list/',
              query: {'mine': _mineOnly ? 'true' : ''},
              emptyMessage: 'Nobody waiting',
              itemBuilder: (context, row) => ListTile(
                leading: CircleAvatar(
                  backgroundColor: row['priority'] == 'normal'
                      ? null
                      : Theme.of(context).colorScheme.errorContainer,
                  child: Text('${row['room_number']}'),
                ),
                title: Text('${row['patient_name']} (${row['patient_number']})'),
                subtitle: Text(
                  '${row['status_display']} · waiting since '
                  '${row['check_in_time'].toString().split('T')[1].substring(0, 5)}'
                  '${row['priority'] == 'normal' ? '' : ' · ${row['priority']}'}',
                ),
                trailing: row['status'] == 'waiting'
                    ? FilledButton(
                        onPressed: () => _callIn(row['id'] as int),
                        child: const Text('Call in'),
                      )
                    : null,
              ),
            ),
            PagedList(
              key: ValueKey('consultations$_mineOnly$_reloadToken'),
              path: '/consultations/api/consultations/',
              query: {'mine': _mineOnly ? 'true' : ''},
              emptyMessage: 'No consultations',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['patient_name']} (${row['patient_number']})'),
                subtitle: Text(
                  '${row['status_display']} · ${row['doctor_name']}\n'
                  '${row['diagnosis'] ?? row['chief_complaint'] ?? ''}',
                ),
                isThreeLine: true,
                onTap: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => ConsultationScreen(consultation: row),
                    ),
                  );
                  setState(() => _reloadToken++);
                },
              ),
            ),
            const ReferralsTab(),
          ],
        ),
      ),
    );
  }
}

class ConsultationScreen extends StatefulWidget {
  const ConsultationScreen({super.key, required this.consultation});

  final Map<String, dynamic> consultation;

  @override
  State<ConsultationScreen> createState() => _ConsultationScreenState();
}

class _ConsultationScreenState extends State<ConsultationScreen> {
  late Map<String, dynamic> _consultation = widget.consultation;
  late final _complaint =
      TextEditingController(text: '${_consultation['chief_complaint'] ?? ''}');
  late final _symptoms =
      TextEditingController(text: '${_consultation['symptoms'] ?? ''}');
  late final _diagnosis =
      TextEditingController(text: '${_consultation['diagnosis'] ?? ''}');
  bool _busy = false;

  @override
  void dispose() {
    _complaint.dispose();
    _symptoms.dispose();
    _diagnosis.dispose();
    super.dispose();
  }

  Future<void> _reload() async {
    try {
      final fresh = await Api.get(
        '/consultations/api/consultations/${_consultation['id']}/',
      );
      if (mounted) setState(() => _consultation = fresh as Map<String, dynamic>);
    } catch (_) {
      // Keep what is on screen.
    }
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      final updated = await Api.patch(
        '/consultations/api/consultations/${_consultation['id']}/',
        {
          'chief_complaint': _complaint.text.trim(),
          'symptoms': _symptoms.text.trim(),
          'diagnosis': _diagnosis.text.trim(),
        },
      );
      if (!mounted) return;
      setState(() => _consultation = updated as Map<String, dynamic>);
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Saved')));
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _setStatus(String status) async {
    setState(() => _busy = true);
    try {
      final updated = await Api.post(
        '/consultations/api/consultations/${_consultation['id']}/set-status/',
        {'status': status},
      );
      if (mounted) {
        setState(() => _consultation = updated as Map<String, dynamic>);
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addNote() async {
    final controller = TextEditingController();
    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add note'),
        content: TextField(
          controller: controller,
          autofocus: true,
          maxLines: 4,
          decoration: const InputDecoration(labelText: 'Note'),
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
    if (saved != true || controller.text.trim().isEmpty) return;

    try {
      await Api.post(
        '/consultations/api/consultations/${_consultation['id']}/notes/',
        {'note': controller.text.trim()},
      );
      await _reload();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final consultation = _consultation;
    final notes =
        ((consultation['notes_log'] as List?) ?? const []).cast<Map<String, dynamic>>();
    final needsAuthorization =
        consultation['requires_authorization'] == true &&
            consultation['authorization_status'] != 'authorized';

    return Scaffold(
      appBar: AppBar(
        title: Text('${consultation['patient_name']}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.note_add_outlined),
            tooltip: 'Add note',
            onPressed: _busy ? null : _addNote,
          ),
        ],
        bottom: _busy
            ? const PreferredSize(
                preferredSize: Size.fromHeight(2),
                child: LinearProgressIndicator(),
              )
            : null,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            '${consultation['status_display']} · ${consultation['doctor_name']}'
            '${consultation['room_number']?.isEmpty ?? true ? '' : ' · Room ${consultation['room_number']}'}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          if (needsAuthorization)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(
                'NHIA patient in a non-NHIA room — desk office authorization '
                'is required.',
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          const SizedBox(height: 12),
          TextField(
            controller: _complaint,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: 'Chief complaint',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _symptoms,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Symptoms',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _diagnosis,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Diagnosis',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _busy ? null : _save,
            child: const Text('Save'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _busy
                ? null
                : () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => ClerkingHistoryScreen(
                          consultation: consultation,
                        ),
                      ),
                    ),
            icon: const Icon(Icons.assignment_outlined),
            label: const Text('Clerking notes'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _busy
                ? null
                : () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => NewReferralScreen(
                          consultation: consultation,
                        ),
                      ),
                    ),
            icon: const Icon(Icons.forward_to_inbox_outlined),
            label: const Text('Refer patient'),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              for (final entry in _consultationStatuses.entries)
                FilledButton.tonal(
                  onPressed: _busy ? null : () => _setStatus(entry.key),
                  child: Text(entry.value),
                ),
            ],
          ),
          if (notes.isNotEmpty) ...[
            const Divider(height: 32),
            Text('Notes', style: Theme.of(context).textTheme.titleMedium),
            for (final note in notes)
              ListTile(
                dense: true,
                title: Text('${note['note']}'),
                subtitle: Text(
                  '${note['created_by_name']} · '
                  '${note['created_at'].toString().split('T').first}',
                ),
              ),
          ],
        ],
      ),
    );
  }
}
