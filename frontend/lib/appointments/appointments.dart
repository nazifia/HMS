import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';
import 'booking.dart';

const _statusActions = {
  'confirmed': 'Confirm',
  'completed': 'Mark completed',
  'no_show': 'Mark no-show',
  'cancelled': 'Cancel',
};

class AppointmentListScreen extends StatefulWidget {
  const AppointmentListScreen({super.key});

  @override
  State<AppointmentListScreen> createState() => _AppointmentListScreenState();
}

class _AppointmentListScreenState extends State<AppointmentListScreen> {
  String _when = 'today';
  bool _mineOnly = false;
  String _search = '';
  int _reloadToken = 0;

  Map<String, String> get _query => {
        'today': _when == 'today' ? 'true' : '',
        'upcoming': _when == 'upcoming' ? 'true' : '',
        'mine': _mineOnly ? 'true' : '',
        'search': _search,
      };

  Future<void> _setStatus(int id, String status) async {
    try {
      await Api.post(
        '/appointments/api/appointments/$id/set-status/',
        {'status': status},
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
    return Scaffold(
      appBar: AppBar(title: const Text('Appointments')),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final booked = await Navigator.of(context).push<bool>(
            MaterialPageRoute(builder: (_) => const BookAppointmentScreen()),
          );
          if (booked == true) setState(() => _reloadToken++);
        },
        child: const Icon(Icons.event_available),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Patient name or ID',
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
                for (final entry in const {
                  'today': 'Today',
                  'upcoming': 'Upcoming',
                  'all': 'All',
                }.entries)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: FilterChip(
                      label: Text(entry.value),
                      selected: _when == entry.key,
                      onSelected: (_) => setState(() => _when = entry.key),
                    ),
                  ),
                const Spacer(),
                FilterChip(
                  label: const Text('Mine'),
                  selected: _mineOnly,
                  onSelected: (on) => setState(() => _mineOnly = on),
                ),
              ],
            ),
          ),
          Expanded(
            child: PagedList(
              key: ValueKey('$_when$_mineOnly$_search$_reloadToken'),
              path: '/appointments/api/appointments/',
              query: _query,
              emptyMessage: 'No appointments',
              itemBuilder: (context, row) => ListTile(
                leading: CircleAvatar(
                  backgroundColor: row['priority'] == 'normal'
                      ? null
                      : Theme.of(context).colorScheme.errorContainer,
                  child: Text(
                    '${row['appointment_date']}'
                        .split('T')[1]
                        .substring(0, 5),
                    style: const TextStyle(fontSize: 11),
                  ),
                ),
                title: Text('${row['patient_name']} (${row['patient_number']})'),
                subtitle: Text(
                  '${row['doctor_name']} · ${row['status_display']}\n'
                  '${row['reason']}',
                ),
                isThreeLine: true,
                trailing: PopupMenuButton<String>(
                  onSelected: (choice) => _setStatus(row['id'] as int, choice),
                  itemBuilder: (_) => [
                    for (final entry in _statusActions.entries)
                      PopupMenuItem(value: entry.key, child: Text(entry.value)),
                  ],
                ),
                onTap: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => AppointmentScreen(appointment: row),
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

class AppointmentScreen extends StatefulWidget {
  const AppointmentScreen({super.key, required this.appointment});

  final Map<String, dynamic> appointment;

  @override
  State<AppointmentScreen> createState() => _AppointmentScreenState();
}

class _AppointmentScreenState extends State<AppointmentScreen> {
  late Map<String, dynamic> _appointment = widget.appointment;
  bool _busy = false;

  Future<void> _setStatus(String status) async {
    setState(() => _busy = true);
    try {
      final updated = await Api.post(
        '/appointments/api/appointments/${_appointment['id']}/set-status/',
        {'status': status},
      );
      setState(() => _appointment = updated as Map<String, dynamic>);
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
    final appointment = _appointment;
    final paid = appointment['payment_verified'] == true;
    final start = '${appointment['appointment_date']}'.split('T');

    return Scaffold(
      appBar: AppBar(
        title: Text('${appointment['patient_name']}'),
        bottom: _busy
            ? const PreferredSize(
                preferredSize: Size.fromHeight(2),
                child: LinearProgressIndicator(),
              )
            : null,
      ),
      body: ListView(
        children: [
          ListTile(
            title: Text('${start[0]} at ${start[1].substring(0, 5)}'),
            subtitle: Text(
              '${appointment['doctor_name']} · ${appointment['status_display']}'
              '${appointment['department_name']?.isEmpty ?? true ? '' : ' · ${appointment['department_name']}'}',
            ),
            trailing: appointment['priority'] == 'normal'
                ? null
                : Chip(label: Text('${appointment['priority']}')),
          ),
          if (!paid)
            ListTile(
              leading: Icon(
                Icons.payments_outlined,
                color: Theme.of(context).colorScheme.error,
              ),
              title: const Text('Consultation fee not settled'),
              subtitle: const Text(
                'The appointment cannot be confirmed or completed until it is paid.',
              ),
            ),
          if (appointment['requires_authorization'] == true)
            ListTile(
              leading: const Icon(Icons.verified_user_outlined),
              title: Text(
                appointment['authorization_code'] == null
                    ? 'NHIA patient — no authorization code attached'
                    : 'NHIA authorization on file',
              ),
            ),
          ListTile(
            title: const Text('Reason'),
            subtitle: Text('${appointment['reason']}'),
          ),
          if (appointment['notes'] != null)
            ListTile(
              title: const Text('Notes'),
              subtitle: Text('${appointment['notes']}'),
            ),
          if (appointment['consulting_room_name']?.isNotEmpty ?? false)
            ListTile(
              leading: const Icon(Icons.meeting_room_outlined),
              title: Text('${appointment['consulting_room_name']}'),
            ),
          const Divider(),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Wrap(
              spacing: 8,
              children: [
                for (final entry in _statusActions.entries)
                  FilledButton.tonal(
                    onPressed: _busy ? null : () => _setStatus(entry.key),
                    child: Text(entry.value),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
