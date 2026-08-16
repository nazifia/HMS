import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

const _packTypes = {
  '': 'All',
  'surgery': 'Surgery',
  'labor': 'Labor',
  'emergency': 'Emergency',
  'routine': 'Routine',
};

const _orderStatuses = {
  '': 'All',
  'pending': 'Pending',
  'in_progress': 'In progress',
  'ready': 'Ready',
  'completed': 'Completed',
};

class PacksScreen extends StatefulWidget {
  const PacksScreen({super.key});

  @override
  State<PacksScreen> createState() => _PacksScreenState();
}

class _PacksScreenState extends State<PacksScreen> {
  String _packType = '';
  String _orderStatus = '';
  int _reloadToken = 0;

  Future<void> _act(String path) async {
    try {
      await Api.post(path);
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
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Medical packs'),
          bottom: const TabBar(tabs: [
            Tab(text: 'Packs'),
            Tab(text: 'Orders'),
          ]),
        ),
        body: TabBarView(
          children: [
            Column(
              children: [
                _chips(_packTypes, _packType, (v) => setState(() => _packType = v)),
                Expanded(
                  child: PagedList(
                    path: '/pharmacy/api/packs/',
                    query: {'pack_type': _packType},
                    emptyMessage: 'No packs',
                    itemBuilder: (context, row) => ListTile(
                      title: Text('${row['name']}'),
                      subtitle: Text(
                        '${row['pack_type_display']} · ${row['item_count']} item(s)'
                        '${row['requires_approval'] == true ? ' · needs approval' : ''}',
                      ),
                      trailing: Text('₦${row['total_value']}'),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => PackScreen(pack: row),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            Column(
              children: [
                _chips(_orderStatuses, _orderStatus,
                    (v) => setState(() => _orderStatus = v)),
                Expanded(
                  child: PagedList(
                    key: ValueKey('orders$_orderStatus$_reloadToken'),
                    path: '/pharmacy/api/pack-orders/',
                    query: {'status': _orderStatus},
                    emptyMessage: 'No pack orders',
                    itemBuilder: (context, row) => ListTile(
                      title: Text('${row['pack_name']} · ${row['patient_name']}'),
                      subtitle: Text(
                        '${row['status_display']} · ordered by ${row['ordered_by_name']}',
                      ),
                      trailing: _orderMenu(row),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _chips(
    Map<String, String> options,
    String selected,
    void Function(String) onSelect,
  ) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          for (final entry in options.entries)
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: FilterChip(
                label: Text(entry.value),
                selected: selected == entry.key,
                onSelected: (_) => onSelect(entry.key),
              ),
            ),
        ],
      ),
    );
  }

  Widget? _orderMenu(Map<String, dynamic> row) {
    final actions = <String, String>{
      if (row['can_be_processed'] == true) 'process': 'Process',
      if (row['can_be_approved'] == true) 'approve': 'Approve',
      if (row['can_be_dispensed'] == true) 'dispense': 'Dispense',
    };
    if (actions.isEmpty) return null;
    return PopupMenuButton<String>(
      onSelected: (choice) =>
          _act('/pharmacy/api/pack-orders/${row['id']}/$choice/'),
      itemBuilder: (_) => [
        for (final entry in actions.entries)
          PopupMenuItem(value: entry.key, child: Text(entry.value)),
      ],
    );
  }
}

class PackScreen extends StatefulWidget {
  const PackScreen({super.key, required this.pack});

  final Map<String, dynamic> pack;

  @override
  State<PackScreen> createState() => _PackScreenState();
}

class _PackScreenState extends State<PackScreen> {
  Map<String, dynamic>? _availability;

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    try {
      final result =
          await Api.get('/pharmacy/api/packs/${widget.pack['id']}/availability/');
      if (mounted) setState(() => _availability = result as Map<String, dynamic>);
    } catch (_) {
      // Availability is advisory; the order endpoint checks again anyway.
    }
  }

  @override
  Widget build(BuildContext context) {
    final pack = widget.pack;
    final items = (pack['items'] as List).cast<Map<String, dynamic>>();
    final availability = _availability;

    return Scaffold(
      appBar: AppBar(title: Text('${pack['name']}')),
      body: ListView(
        children: [
          ListTile(
            title: Text('${pack['pack_type_display']} · ${pack['risk_level']} risk'),
            subtitle: Text('${pack['description'] ?? ''}'),
            trailing: Text('₦${pack['total_value']}'),
          ),
          if (availability != null)
            ListTile(
              leading: Icon(
                availability['can_order'] == true
                    ? Icons.check_circle
                    : Icons.error_outline,
                color: availability['can_order'] == true
                    ? Colors.green
                    : Theme.of(context).colorScheme.error,
              ),
              title: Text('${availability['message']}'),
            ),
          const Divider(),
          for (final item in items)
            ListTile(
              title: Text(
                '${item['medication_name']} ${item['medication_strength'] ?? ''}',
              ),
              subtitle: Text(
                '${item['item_type']}'
                '${item['is_critical'] == true ? ' · critical' : ''}'
                '${item['is_optional'] == true ? ' · optional' : ''}'
                '${item['usage_instructions'] == null ? '' : '\n${item['usage_instructions']}'}',
              ),
              isThreeLine: item['usage_instructions'] != null,
              trailing: Text('× ${item['quantity']}'),
            ),
        ],
      ),
    );
  }
}
