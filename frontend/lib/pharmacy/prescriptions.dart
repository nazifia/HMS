import 'package:flutter/material.dart';

import '../paged_list.dart';
import '../page_screen.dart';
import 'carts.dart';

const _statusFilters = {
  '': 'All',
  'pending': 'Pending',
  'approved': 'Approved',
  'partially_dispensed': 'Partial',
  'dispensed': 'Dispensed',
  'cancelled': 'Cancelled',
};

class PrescriptionListScreen extends StatefulWidget {
  const PrescriptionListScreen({super.key});

  @override
  State<PrescriptionListScreen> createState() => _PrescriptionListScreenState();
}

class _PrescriptionListScreenState extends State<PrescriptionListScreen> {
  String _search = '';
  String _status = '';
  String _payment = '';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Prescriptions')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Patient name, patient ID or diagnosis',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onSubmitted: (v) => setState(() => _search = v.trim()),
            ),
          ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              children: [
                for (final entry in _statusFilters.entries)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: FilterChip(
                      label: Text(entry.value),
                      selected: _status == entry.key,
                      onSelected: (_) => setState(() => _status = entry.key),
                    ),
                  ),
                const SizedBox(width: 8),
                FilterChip(
                  label: const Text('Unpaid'),
                  selected: _payment == 'unpaid',
                  onSelected: (on) =>
                      setState(() => _payment = on ? 'unpaid' : ''),
                ),
              ],
            ),
          ),
          Expanded(
            child: PagedList(
              path: '/pharmacy/api/prescriptions/',
              query: {
                'search': _search,
                'status': _status,
                'payment_status': _payment,
              },
              emptyMessage: 'No prescriptions match',
              itemBuilder: (context, row) => _PrescriptionTile(row: row),
            ),
          ),
        ],
      ),
    );
  }
}

class _PrescriptionTile extends StatelessWidget {
  const _PrescriptionTile({required this.row});

  final Map<String, dynamic> row;

  @override
  Widget build(BuildContext context) {
    final items = (row['items'] as List?) ?? const [];
    final unpaid = row['payment_status'] == 'unpaid';
    return ListTile(
      title: Text('${row['patient_name']} (${row['patient_number']})'),
      subtitle: Text(
        '${row['prescription_date'].toString().split('T').first} · '
        '${items.length} item(s)'
        '${row['diagnosis'] == null ? '' : ' · ${row['diagnosis']}'}',
      ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(row['status_display'] ?? ''),
          Text(
            row['payment_status_display'] ?? '',
            style: TextStyle(
              fontSize: 12,
              color: unpaid
                  ? Theme.of(context).colorScheme.error
                  : Theme.of(context).hintColor,
            ),
          ),
        ],
      ),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PrescriptionDetailScreen(prescription: row),
        ),
      ),
    );
  }
}

class PrescriptionDetailScreen extends StatelessWidget {
  const PrescriptionDetailScreen({super.key, required this.prescription});

  final Map<String, dynamic> prescription;

  @override
  Widget build(BuildContext context) {
    final id = prescription['id'];
    final items = ((prescription['items'] as List?) ?? const [])
        .cast<Map<String, dynamic>>();

    return Scaffold(
      appBar: AppBar(
        title: Text('${prescription['patient_name']}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.open_in_new),
            tooltip: 'Open server page',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => PageScreen(
                  title: 'Prescription',
                  path: '/pharmacy/prescriptions/$id/',
                ),
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => createCartForPrescription(context, id as int),
        icon: const Icon(Icons.shopping_cart_outlined),
        label: const Text('Dispensing cart'),
      ),
      body: ListView(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _row('Patient ID', prescription['patient_number']),
                _row('Doctor', prescription['doctor_name']),
                _row(
                  'Date',
                  prescription['prescription_date'].toString().split('T').first,
                ),
                _row('Diagnosis', prescription['diagnosis']),
                _row('Status', prescription['status_display']),
                _row('Payment', prescription['payment_status_display']),
                _row('Type', prescription['prescription_type']),
                _row('Authorization', prescription['authorization_status']),
                if (prescription['notes'] != null)
                  _row('Notes', prescription['notes']),
              ],
            ),
          ),
          const Divider(),
          for (final item in items) _ItemTile(item: item),
        ],
      ),
    );
  }

  Widget _row(String label, Object? value) {
    if (value == null || value.toString().isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 120, child: Text(label)),
          Expanded(
            child: Text(
              '$value',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _ItemTile extends StatelessWidget {
  const _ItemTile({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final medication = item['medication'] as Map<String, dynamic>?;
    final dispensed = item['quantity_dispensed_so_far'] ?? 0;
    final quantity = item['quantity'] ?? 0;
    return ListTile(
      leading: Icon(
        item['is_dispensed'] == true
            ? Icons.check_circle
            : Icons.radio_button_unchecked,
        color: item['is_dispensed'] == true ? Colors.green : null,
      ),
      title: Text(
        '${medication?['name'] ?? 'Unknown'} ${medication?['strength'] ?? ''}',
      ),
      subtitle: Text(
        [
          item['dosage'],
          item['frequency'],
          item['duration'],
          item['instructions'],
        ].where((v) => v != null && '$v'.isNotEmpty).join(' · '),
      ),
      trailing: Text('$dispensed / $quantity'),
    );
  }
}
