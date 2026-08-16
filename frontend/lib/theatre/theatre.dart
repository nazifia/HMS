import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';
import 'checklist.dart';

const _surgeryStatuses = {
  '': 'All',
  'scheduled': 'Scheduled',
  'pending': 'Pending',
  'in_progress': 'In progress',
  'completed': 'Completed',
};

/// Statuses a theatre moves a surgery through by hand.
const _nextStatuses = {
  'in_progress': 'Start surgery',
  'completed': 'Mark completed',
  'postponed': 'Postpone',
  'cancelled': 'Cancel',
};

/// The theatre list for one day — what the board on the wall shows.
class TheatreListScreen extends StatefulWidget {
  const TheatreListScreen({super.key});

  @override
  State<TheatreListScreen> createState() => _TheatreListScreenState();
}

class _TheatreListScreenState extends State<TheatreListScreen> {
  DateTime _date = DateTime.now();
  Map<String, dynamic>? _data;
  String? _error;

  String get _dateText =>
      '${_date.year}-${_date.month.toString().padLeft(2, '0')}'
      '-${_date.day.toString().padLeft(2, '0')}';

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    try {
      final data = await Api.get('/theatre/api/theatres/today/', {
        'date': _dateText,
      });
      if (!mounted) return;
      setState(() {
        _data = data as Map<String, dynamic>;
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _shiftDay(int days) async {
    setState(() => _date = _date.add(Duration(days: days)));
    await _reload();
  }

  @override
  Widget build(BuildContext context) {
    final data = _data;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Theatre list'),
        actions: [
          IconButton(
            icon: const Icon(Icons.list_alt),
            tooltip: 'All surgeries',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const SurgeryListScreen()),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.chevron_left),
                onPressed: () => _shiftDay(-1),
              ),
              Text(_dateText, style: Theme.of(context).textTheme.titleMedium),
              IconButton(
                icon: const Icon(Icons.chevron_right),
                onPressed: () => _shiftDay(1),
              ),
            ],
          ),
          if (_error != null)
            Expanded(child: Center(child: Text(_error!)))
          else if (data == null)
            const Expanded(child: Center(child: CircularProgressIndicator()))
          else if ((data['results'] as List).isEmpty)
            const Expanded(child: Center(child: Text('Nothing booked')))
          else
            Expanded(
              child: RefreshIndicator(
                onRefresh: _reload,
                child: ListView.separated(
                  itemCount: (data['results'] as List).length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, i) {
                    final row = (data['results'] as List)[i]
                        as Map<String, dynamic>;
                    return _SurgeryTile(
                      row: row,
                      onOpen: () async {
                        await Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) =>
                                SurgeryScreen(surgeryId: row['id'] as int),
                          ),
                        );
                        _reload();
                      },
                    );
                  },
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Every surgery, with status filters and search.
class SurgeryListScreen extends StatefulWidget {
  const SurgeryListScreen({super.key});

  @override
  State<SurgeryListScreen> createState() => _SurgeryListScreenState();
}

class _SurgeryListScreenState extends State<SurgeryListScreen> {
  String _status = '';
  String _search = '';
  int _reloadToken = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Surgeries')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Patient, ID or procedure',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onSubmitted: (v) => setState(() => _search = v.trim()),
            ),
          ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                for (final entry in _surgeryStatuses.entries)
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
              path: '/theatre/api/surgeries/',
              query: {'status': _status, 'search': _search},
              emptyMessage: 'No surgeries',
              itemBuilder: (context, row) => _SurgeryTile(
                row: row,
                onOpen: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => SurgeryScreen(surgeryId: row['id'] as int),
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

class _SurgeryTile extends StatelessWidget {
  const _SurgeryTile({required this.row, required this.onOpen});

  final Map<String, dynamic> row;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final time = row['scheduled_date'].toString().replaceFirst('T', ' ');
    return ListTile(
      title: Text('${row['patient_name']} (${row['patient_number']})'),
      subtitle: Text(
        '${row['surgery_type_name']} · ${row['theatre_name']}\n'
        '${time.split('.').first} · ${row['status_display']}',
      ),
      isThreeLine: true,
      trailing: row['can_perform'] == true
          ? null
          : Icon(Icons.lock_outline, color: Theme.of(context).colorScheme.error),
      onTap: onOpen,
    );
  }
}

class SurgeryScreen extends StatefulWidget {
  const SurgeryScreen({super.key, required this.surgeryId});

  final int surgeryId;

  @override
  State<SurgeryScreen> createState() => _SurgeryScreenState();
}

class _SurgeryScreenState extends State<SurgeryScreen> {
  Map<String, dynamic>? _surgery;
  String? _error;
  bool _busy = false;

  String get _base => '/theatre/api/surgeries/${widget.surgeryId}';

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    try {
      final surgery = await Api.get('$_base/');
      if (!mounted) return;
      setState(() {
        _surgery = surgery as Map<String, dynamic>;
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

  Future<void> _addPostOpNote() async {
    final notes = TextEditingController();
    final complications = TextEditingController();
    final followUp = TextEditingController();
    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Post-operative note'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: notes,
                autofocus: true,
                maxLines: 4,
                decoration: const InputDecoration(labelText: 'Notes'),
              ),
              TextField(
                controller: complications,
                decoration: const InputDecoration(labelText: 'Complications'),
              ),
              TextField(
                controller: followUp,
                decoration: const InputDecoration(labelText: 'Follow-up'),
              ),
            ],
          ),
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
    if (saved != true) return;
    await _act(() => Api.post('$_base/post-op-note/', {
          'notes': notes.text.trim(),
          'complications': complications.text.trim(),
          'follow_up_instructions': followUp.text.trim(),
        }));
  }

  @override
  Widget build(BuildContext context) {
    final surgery = _surgery;
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Surgery')),
        body: Center(child: Text(_error!)),
      );
    }
    if (surgery == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final team = (surgery['team_members'] as List).cast<Map<String, dynamic>>();
    final equipment =
        (surgery['equipment_used'] as List).cast<Map<String, dynamic>>();
    final packs = (surgery['pack_orders'] as List).cast<Map<String, dynamic>>();
    final blocked = '${surgery['blocked_reason'] ?? ''}';

    return Scaffold(
      appBar: AppBar(
        title: Text('${surgery['patient_name']}'),
        actions: [
          PopupMenuButton<String>(
            enabled: !_busy,
            onSelected: (choice) => _act(
              () => Api.post('$_base/set-status/', {'status': choice}),
            ),
            itemBuilder: (_) => [
              for (final entry in _nextStatuses.entries)
                PopupMenuItem(value: entry.key, child: Text(entry.value)),
            ],
          ),
        ],
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
              title: Text('${surgery['surgery_type_name']}'),
              subtitle: Text(
                '${surgery['theatre_name']} · ${surgery['status_display']}\n'
                '${surgery['scheduled_date'].toString().replaceFirst('T', ' ').split('.').first}'
                ' · ${surgery['expected_duration']}',
              ),
              isThreeLine: true,
              trailing: Text('₦${surgery['surgery_fee']}'),
            ),
            if (blocked.isNotEmpty)
              ListTile(
                leading: Icon(
                  Icons.lock_outline,
                  color: Theme.of(context).colorScheme.error,
                ),
                title: Text(blocked),
              ),
            ListTile(
              leading: const Icon(Icons.medical_services_outlined),
              title: Text(
                'Surgeon: ${surgery['surgeon_name'].toString().isEmpty ? '—' : surgery['surgeon_name']}',
              ),
              subtitle: Text(
                'Anaesthetist: '
                '${surgery['anesthetist_name'].toString().isEmpty ? '—' : surgery['anesthetist_name']}',
              ),
            ),
            const Divider(),
            ListTile(
              leading: Icon(
                surgery['checklist_complete'] == true
                    ? Icons.checklist_rtl
                    : Icons.checklist,
                color: surgery['checklist_complete'] == true ? Colors.green : null,
              ),
              title: const Text('Pre-operative checklist'),
              subtitle: Text(
                surgery['checklist_complete'] == true
                    ? 'Complete'
                    : 'Not complete',
              ),
              onTap: () async {
                await Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => ChecklistScreen(
                      surgeryId: widget.surgeryId,
                      surgery: surgery,
                    ),
                  ),
                );
                _reload();
              },
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.groups_outlined),
              title: const Text('Surgical team'),
              subtitle: Text(
                team.isEmpty
                    ? 'Nobody assigned'
                    : team
                        .map((m) => '${m['staff_name']} (${m['role_display']})')
                        .join('\n'),
              ),
              isThreeLine: team.isNotEmpty,
            ),
            if (equipment.isNotEmpty)
              ListTile(
                leading: const Icon(Icons.handyman_outlined),
                title: const Text('Equipment'),
                subtitle: Text(
                  equipment
                      .map((e) => '${e['equipment_name']} ×${e['quantity_used']}')
                      .join('\n'),
                ),
              ),
            if (packs.isNotEmpty)
              ListTile(
                leading: const Icon(Icons.inventory_2_outlined),
                title: const Text('Medical packs'),
                subtitle: Text(
                  packs
                      .map((p) => '${p['pack_name']} · ${p['status']}')
                      .join('\n'),
                ),
              ),
            if ('${surgery['pre_surgery_notes'] ?? ''}'.isNotEmpty)
              ListTile(
                leading: const Icon(Icons.sticky_note_2_outlined),
                title: Text('${surgery['pre_surgery_notes']}'),
                subtitle: const Text('Pre-surgery notes'),
              ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: FilledButton.tonal(
                onPressed: _busy ? null : _addPostOpNote,
                child: const Text('Post-operative note'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
