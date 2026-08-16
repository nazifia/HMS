import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

/// Reusable dispensary picker — several pharmacy screens are scoped to one.
Future<Map<String, dynamic>?> pickDispensary(BuildContext context) async {
  final data = await Api.get('/pharmacy/api/dispensaries/');
  final list = (data is Map ? data['results'] : data) as List;
  if (!context.mounted) return null;
  return showDialog<Map<String, dynamic>>(
    context: context,
    builder: (context) => SimpleDialog(
      title: const Text('Dispensary'),
      children: [
        for (final d in list.cast<Map<String, dynamic>>())
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, d),
            child: Text('${d['name']}'),
          ),
      ],
    ),
  );
}

class InventoryScreen extends StatefulWidget {
  const InventoryScreen({super.key});

  @override
  State<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen> {
  Map<String, dynamic>? _dispensary;
  String _search = '';
  bool _lowOnly = false;
  bool _expiringOnly = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_dispensary == null
            ? 'Inventory'
            : 'Inventory · ${_dispensary!['name']}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.store_outlined),
            tooltip: 'Dispensary',
            onPressed: () async {
              final chosen = await pickDispensary(context);
              if (chosen != null) setState(() => _dispensary = chosen);
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Medication, generic name or manufacturer',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onSubmitted: (v) => setState(() => _search = v.trim()),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              children: [
                FilterChip(
                  label: const Text('Low stock'),
                  selected: _lowOnly,
                  onSelected: (on) => setState(() => _lowOnly = on),
                ),
                const SizedBox(width: 8),
                FilterChip(
                  label: const Text('Expiring 90d'),
                  selected: _expiringOnly,
                  onSelected: (on) => setState(() => _expiringOnly = on),
                ),
              ],
            ),
          ),
          Expanded(
            child: PagedList(
              path: '/pharmacy/api/inventory/',
              query: {
                'dispensary': '${_dispensary?['id'] ?? ''}',
                'search': _search,
                'low_stock': _lowOnly ? 'true' : '',
                'expiring': _expiringOnly ? 'true' : '',
              },
              emptyMessage: 'No stock matches',
              itemBuilder: (context, row) {
                final medication = row['medication'] as Map<String, dynamic>;
                final low = row['is_low_stock'] == true;
                return ListTile(
                  title: Text('${medication['name']} ${medication['strength'] ?? ''}'),
                  subtitle: Text(
                    '${row['dispensary_name']} · reorder at ${row['reorder_level']}'
                    '${row['expiry_date'] == null ? '' : ' · expires ${row['expiry_date']}'}'
                    '${row['is_expired'] == true ? ' · EXPIRED' : ''}',
                  ),
                  trailing: Text(
                    '${row['stock_quantity']}',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: low ? Theme.of(context).colorScheme.error : null,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
