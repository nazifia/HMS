import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

class MedicationListScreen extends StatefulWidget {
  const MedicationListScreen({super.key});

  @override
  State<MedicationListScreen> createState() => _MedicationListScreenState();
}

class _MedicationListScreenState extends State<MedicationListScreen> {
  String _search = '';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Medications')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Name, generic name or category',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onSubmitted: (v) => setState(() => _search = v.trim()),
            ),
          ),
          Expanded(
            child: PagedList(
              path: '/pharmacy/api/medications/',
              query: {'search': _search},
              emptyMessage: 'No medications match',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['name']} ${row['strength'] ?? ''}'),
                subtitle: Text(
                  [row['generic_name'], row['dosage_form'], row['category']?['name']]
                      .where((v) => v != null && '$v'.isNotEmpty)
                      .join(' · '),
                ),
                trailing: Text('₦${row['price']}'),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => MedicationStockScreen(medication: row),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Stock for one medication across every active dispensary.
class MedicationStockScreen extends StatefulWidget {
  const MedicationStockScreen({super.key, required this.medication});

  final Map<String, dynamic> medication;

  @override
  State<MedicationStockScreen> createState() => _MedicationStockScreenState();
}

class _MedicationStockScreenState extends State<MedicationStockScreen> {
  late Future<dynamic> _stock;

  @override
  void initState() {
    super.initState();
    _stock = Api.get('/pharmacy/api/medications/${widget.medication['id']}/stock/');
  }

  @override
  Widget build(BuildContext context) {
    final medication = widget.medication;
    final reorderLevel = (medication['reorder_level'] as num?)?.toInt() ?? 0;

    return Scaffold(
      appBar: AppBar(title: Text('${medication['name']}')),
      body: FutureBuilder<dynamic>(
        future: _stock,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('${snapshot.error}'));
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final rows = (snapshot.data as List).cast<Map<String, dynamic>>();
          final total = rows.fold<int>(
            0,
            (sum, r) => sum + (r['stock_quantity'] as int),
          );
          return ListView(
            children: [
              ListTile(
                title: Text(
                  '${medication['strength'] ?? ''} ${medication['dosage_form'] ?? ''}',
                ),
                subtitle: Text(
                  'Total in stock: $total · reorder level: $reorderLevel',
                ),
                trailing: Text('₦${medication['price']}'),
              ),
              const Divider(),
              for (final row in rows)
                ListTile(
                  title: Text('${row['dispensary']}'),
                  trailing: Text(
                    '${row['stock_quantity']}',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: (row['stock_quantity'] as int) <= reorderLevel
                          ? Theme.of(context).colorScheme.error
                          : null,
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}
