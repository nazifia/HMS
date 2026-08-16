import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

/// Referrals in and out. The server decides who may accept what, and the tile
/// only offers Accept when it says so.
class ReferralsTab extends StatefulWidget {
  const ReferralsTab({super.key});

  @override
  State<ReferralsTab> createState() => _ReferralsTabState();
}

class _ReferralsTabState extends State<ReferralsTab> {
  String _direction = 'incoming';
  int _reloadToken = 0;

  Future<void> _setStatus(int id, String status, {String notes = ''}) async {
    try {
      await Api.post(
        '/consultations/api/referrals/$id/set-status/',
        {'status': status, 'notes': notes},
      );
      setState(() => _reloadToken++);
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  Future<void> _accept(Map<String, dynamic> referral) async {
    final controller = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Accept referral for ${referral['patient_name']}'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(labelText: 'Notes (optional)'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Accept'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await _setStatus(
      referral['id'] as int, 'accepted', notes: controller.text.trim(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            children: [
              for (final entry in const {
                'incoming': 'To me',
                'outgoing': 'Sent',
              }.entries)
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: FilterChip(
                    label: Text(entry.value),
                    selected: _direction == entry.key,
                    onSelected: (_) => setState(() => _direction = entry.key),
                  ),
                ),
            ],
          ),
        ),
        Expanded(
          child: PagedList(
            key: ValueKey('$_direction$_reloadToken'),
            path: '/consultations/api/referrals/',
            query: {_direction: 'true'},
            emptyMessage: 'No referrals',
            itemBuilder: (context, row) {
              final blocked = row['requires_authorization'] == true &&
                  row['authorization_status'] != 'authorized';
              return ListTile(
                title: Text('${row['patient_name']} → ${row['destination']}'),
                subtitle: Text(
                  '${row['status_display']} · from ${row['referring_doctor_name']}\n'
                  '${row['reason']}'
                  '${blocked ? '\nAwaiting desk office authorization' : ''}',
                ),
                isThreeLine: true,
                trailing: row['status'] == 'pending' && row['can_accept'] == true
                    ? PopupMenuButton<String>(
                        onSelected: (choice) => choice == 'accepted'
                            ? _accept(row)
                            : _setStatus(row['id'] as int, choice),
                        itemBuilder: (_) => const [
                          PopupMenuItem(value: 'accepted', child: Text('Accept')),
                          PopupMenuItem(
                            value: 'cancelled',
                            child: Text('Decline'),
                          ),
                        ],
                      )
                    : null,
              );
            },
          ),
        ),
      ],
    );
  }
}

class NewReferralScreen extends StatefulWidget {
  const NewReferralScreen({super.key, required this.consultation});

  final Map<String, dynamic> consultation;

  @override
  State<NewReferralScreen> createState() => _NewReferralScreenState();
}

class _NewReferralScreenState extends State<NewReferralScreen> {
  Map<String, dynamic>? _department;
  final _reason = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  Future<void> _pickDepartment() async {
    // Departments come from the consulting-room list, which every clinical
    // user may read.
    final rooms = await Api.get('/consultations/api/rooms/');
    final list = ((rooms is Map ? rooms['results'] : rooms) as List)
        .cast<Map<String, dynamic>>();
    final departments = <int, String>{};
    for (final room in list) {
      if (room['department'] != null) {
        departments[room['department'] as int] = '${room['department_name']}';
      }
    }
    if (!mounted) return;
    if (departments.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No departments available')),
      );
      return;
    }
    final chosen = await showDialog<MapEntry<int, String>>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Refer to department'),
        children: [
          for (final entry in departments.entries)
            SimpleDialogOption(
              onPressed: () => Navigator.pop(context, entry),
              child: Text(entry.value),
            ),
        ],
      ),
    );
    if (chosen != null) {
      setState(() => _department = {'id': chosen.key, 'name': chosen.value});
    }
  }

  Future<void> _submit() async {
    if (_department == null || _reason.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pick a department and give a reason')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      await Api.post('/consultations/api/referrals/', {
        'consultation': widget.consultation['id'],
        'patient': widget.consultation['patient'],
        'referral_type': 'department',
        'referred_to_department': _department!['id'],
        'reason': _reason.text.trim(),
      });
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Referred to ${_department!['name']}')),
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
      appBar: AppBar(title: const Text('Refer patient')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ListTile(
            leading: const Icon(Icons.person_outline),
            title: Text('${widget.consultation['patient_name']}'),
            subtitle: Text('${widget.consultation['patient_number']}'),
          ),
          ListTile(
            leading: const Icon(Icons.apartment_outlined),
            title: Text(_department?['name'] ?? 'Department'),
            onTap: _pickDepartment,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _reason,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Reason for referral',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: const Text('Send referral'),
          ),
        ],
      ),
    );
  }
}
