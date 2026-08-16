import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';
import 'inventory.dart';

/// Who dispensed what, with running totals for the current filter.
class DispensingLogScreen extends StatefulWidget {
  const DispensingLogScreen({super.key});

  @override
  State<DispensingLogScreen> createState() => _DispensingLogScreenState();
}

class _DispensingLogScreenState extends State<DispensingLogScreen> {
  Map<String, dynamic>? _dispensary;
  bool _mineOnly = false;
  bool _todayOnly = true;

  Map<String, String> get _query {
    final today = DateTime.now().toIso8601String().split('T').first;
    return {
      'dispensary': '${_dispensary?['id'] ?? ''}',
      'mine': _mineOnly ? 'true' : '',
      'date_from': _todayOnly ? today : '',
    };
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dispensing log'),
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
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                FilterChip(
                  label: const Text('Today'),
                  selected: _todayOnly,
                  onSelected: (on) => setState(() => _todayOnly = on),
                ),
                const SizedBox(width: 8),
                FilterChip(
                  label: const Text('Mine'),
                  selected: _mineOnly,
                  onSelected: (on) => setState(() => _mineOnly = on),
                ),
                if (_dispensary != null) ...[
                  const SizedBox(width: 8),
                  InputChip(
                    label: Text('${_dispensary!['name']}'),
                    onDeleted: () => setState(() => _dispensary = null),
                  ),
                ],
              ],
            ),
          ),
          _Summary(query: _query),
          const Divider(height: 1),
          Expanded(
            child: PagedList(
              path: '/pharmacy/api/dispensing-logs/',
              query: _query,
              emptyMessage: 'Nothing dispensed yet',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['medication_name']} × ${row['dispensed_quantity']}'),
                subtitle: Text(
                  '${row['patient_name']} · ${row['dispensed_by_name']}'
                  '${row['dispensary_name']?.isEmpty ?? true ? '' : ' · ${row['dispensary_name']}'}',
                ),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('₦${row['total_price_for_this_log']}'),
                    Text(
                      '${row['dispensed_date']}'.split('T').first,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Summary extends StatefulWidget {
  const _Summary({required this.query});

  final Map<String, String> query;

  @override
  State<_Summary> createState() => _SummaryState();
}

class _SummaryState extends State<_Summary> {
  Map<String, dynamic>? _totals;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(_Summary old) {
    super.didUpdateWidget(old);
    if (old.query.toString() != widget.query.toString()) _load();
  }

  Future<void> _load() async {
    try {
      final totals =
          await Api.get('/pharmacy/api/dispensing-logs/summary/', widget.query);
      if (mounted) setState(() => _totals = totals as Map<String, dynamic>);
    } catch (_) {
      if (mounted) setState(() => _totals = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final totals = _totals;
    if (totals == null) return const SizedBox(height: 8);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text('${totals['entries']} entries'),
          Text('${totals['quantity']} units'),
          Text(
            '₦${totals['value']}',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
