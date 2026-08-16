import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';
import 'inventory.dart';

const _transferStatuses = {
  '': 'All',
  'pending': 'Pending',
  'in_transit': 'In transit',
  'completed': 'Completed',
  'rejected': 'Rejected',
};

/// Stock movements: dispensary to dispensary, and bulk store to dispensary.
class TransfersScreen extends StatefulWidget {
  const TransfersScreen({super.key});

  @override
  State<TransfersScreen> createState() => _TransfersScreenState();
}

class _TransfersScreenState extends State<TransfersScreen> {
  String _status = '';
  int _reloadToken = 0;

  void _refresh() => setState(() => _reloadToken++);

  Future<void> _act(String path) async {
    try {
      await Api.post(path);
      _refresh();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  Future<void> _reject(int id) async {
    final controller = TextEditingController();
    final reason = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Reject transfer'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Reason'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Reject'),
          ),
        ],
      ),
    );
    if (reason == null) return;
    try {
      await Api.post('/pharmacy/api/transfers/$id/reject/', {'reason': reason});
      _refresh();
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
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Stock transfers'),
          bottom: const TabBar(tabs: [
            Tab(text: 'Between dispensaries'),
            Tab(text: 'From bulk store'),
          ]),
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: () async {
            final created = await Navigator.of(context).push<bool>(
              MaterialPageRoute(builder: (_) => const NewTransferScreen()),
            );
            if (created == true) _refresh();
          },
          child: const Icon(Icons.add),
        ),
        body: Column(
          children: [
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(
                children: [
                  for (final entry in _transferStatuses.entries)
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
              child: TabBarView(
                children: [
                  PagedList(
                    key: ValueKey('inter$_status$_reloadToken'),
                    path: '/pharmacy/api/transfers/',
                    query: {'status': _status},
                    emptyMessage: 'No transfers',
                    itemBuilder: (context, row) => _TransferTile(
                      row: row,
                      route: '${row['from_dispensary_name']} → ${row['to_dispensary_name']}',
                      onApprove: () =>
                          _act('/pharmacy/api/transfers/${row['id']}/approve/'),
                      onExecute: () =>
                          _act('/pharmacy/api/transfers/${row['id']}/execute/'),
                      onReject: () => _reject(row['id'] as int),
                    ),
                  ),
                  PagedList(
                    key: ValueKey('bulk$_status$_reloadToken'),
                    path: '/pharmacy/api/bulk-transfers/',
                    query: {'status': _status},
                    emptyMessage: 'No transfers',
                    itemBuilder: (context, row) => _TransferTile(
                      row: row,
                      route: '${row['from_bulk_store_name']} → ${row['to_dispensary_name']}',
                      onApprove: () => _act(
                          '/pharmacy/api/bulk-transfers/${row['id']}/approve/'),
                      onExecute: () => _act(
                          '/pharmacy/api/bulk-transfers/${row['id']}/execute/'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TransferTile extends StatelessWidget {
  const _TransferTile({
    required this.row,
    required this.route,
    required this.onApprove,
    required this.onExecute,
    this.onReject,
  });

  final Map<String, dynamic> row;
  final String route;
  final VoidCallback onApprove;
  final VoidCallback onExecute;
  final VoidCallback? onReject;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      title: Text(
        '${row['quantity']} × ${row['medication_name']} ${row['medication_strength'] ?? ''}',
      ),
      subtitle: Text(
        '$route · ${row['status_display']}'
        '${row['rejection_reason'] == null ? '' : '\n${row['rejection_reason']}'}',
      ),
      isThreeLine: row['rejection_reason'] != null,
      trailing: (row['can_approve'] == true || row['can_execute'] == true)
          ? PopupMenuButton<String>(
              onSelected: (choice) => switch (choice) {
                'approve' => onApprove(),
                'execute' => onExecute(),
                _ => onReject?.call(),
              },
              itemBuilder: (_) => [
                if (row['can_approve'] == true)
                  const PopupMenuItem(value: 'approve', child: Text('Approve')),
                if (row['can_reject'] == true && onReject != null)
                  const PopupMenuItem(value: 'reject', child: Text('Reject')),
                if (row['can_execute'] == true)
                  const PopupMenuItem(
                    value: 'execute',
                    child: Text('Execute (move stock)'),
                  ),
              ],
            )
          : null,
    );
  }
}

/// Request stock from another dispensary.
class NewTransferScreen extends StatefulWidget {
  const NewTransferScreen({super.key});

  @override
  State<NewTransferScreen> createState() => _NewTransferScreenState();
}

class _NewTransferScreenState extends State<NewTransferScreen> {
  Map<String, dynamic>? _from;
  Map<String, dynamic>? _to;
  Map<String, dynamic>? _medication;
  final _quantity = TextEditingController(text: '1');
  final _notes = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _quantity.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _pickMedication() async {
    final controller = TextEditingController();
    final query = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Find medication'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Name'),
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Search'),
          ),
        ],
      ),
    );
    if (query == null || query.isEmpty) return;

    final data = await Api.get('/pharmacy/api/medications/', {'search': query});
    final results = (data['results'] as List).cast<Map<String, dynamic>>();
    if (!mounted) return;
    final chosen = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => SimpleDialog(
        title: Text('Matches for "$query"'),
        children: [
          for (final med in results)
            SimpleDialogOption(
              onPressed: () => Navigator.pop(context, med),
              child: Text('${med['name']} ${med['strength'] ?? ''}'),
            ),
        ],
      ),
    );
    if (chosen != null) setState(() => _medication = chosen);
  }

  Future<void> _submit() async {
    final quantity = int.tryParse(_quantity.text.trim()) ?? 0;
    if (_from == null || _to == null || _medication == null || quantity <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pick source, destination, medication and quantity')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final result = await Api.post('/pharmacy/api/transfers/', {
        'medication': _medication!['id'],
        'from_dispensary': _from!['id'],
        'to_dispensary': _to!['id'],
        'quantity': quantity,
        'notes': _notes.text.trim(),
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${result['availability_message']}')),
      );
      Navigator.pop(context, true);
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
      appBar: AppBar(title: const Text('New transfer')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ListTile(
            leading: const Icon(Icons.upload_outlined),
            title: Text(_from?['name'] ?? 'From dispensary'),
            onTap: () async {
              final chosen = await pickDispensary(context);
              if (chosen != null) setState(() => _from = chosen);
            },
          ),
          ListTile(
            leading: const Icon(Icons.download_outlined),
            title: Text(_to?['name'] ?? 'To dispensary'),
            onTap: () async {
              final chosen = await pickDispensary(context);
              if (chosen != null) setState(() => _to = chosen);
            },
          ),
          ListTile(
            leading: const Icon(Icons.medication_outlined),
            title: Text(_medication == null
                ? 'Medication'
                : '${_medication!['name']} ${_medication!['strength'] ?? ''}'),
            onTap: _pickMedication,
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _quantity,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Quantity',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
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
            child: const Text('Request transfer'),
          ),
        ],
      ),
    );
  }
}
