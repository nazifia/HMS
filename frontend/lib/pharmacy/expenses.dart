import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

const _expenseTypes = {
  'operational': 'Operational',
  'equipment': 'Equipment',
  'maintenance': 'Maintenance',
  'utility': 'Utilities',
  'salary': 'Staff salary',
  'supplies': 'Medical supplies',
  'purchase': 'Medication purchase',
  'other': 'Other',
};

class ExpensesScreen extends StatefulWidget {
  const ExpensesScreen({super.key});

  @override
  State<ExpensesScreen> createState() => _ExpensesScreenState();
}

class _ExpensesScreenState extends State<ExpensesScreen> {
  String _type = '';
  bool _pendingOnly = false;
  int _reloadToken = 0;

  Map<String, String> get _query => {
        'expense_type': _type,
        'payment_status': _pendingOnly ? 'pending' : '',
      };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pharmacy expenses')),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final added = await Navigator.of(context).push<bool>(
            MaterialPageRoute(builder: (_) => const NewExpenseScreen()),
          );
          if (added == true) setState(() => _reloadToken++);
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
                FilterChip(
                  label: const Text('Unpaid'),
                  selected: _pendingOnly,
                  onSelected: (on) => setState(() => _pendingOnly = on),
                ),
                const SizedBox(width: 12),
                for (final entry in _expenseTypes.entries)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: FilterChip(
                      label: Text(entry.value),
                      selected: _type == entry.key,
                      onSelected: (on) =>
                          setState(() => _type = on ? entry.key : ''),
                    ),
                  ),
              ],
            ),
          ),
          _ExpenseSummary(query: _query, reloadToken: _reloadToken),
          const Divider(height: 1),
          Expanded(
            child: PagedList(
              key: ValueKey('$_type$_pendingOnly$_reloadToken'),
              path: '/pharmacy/api/expenses/',
              query: _query,
              emptyMessage: 'No expenses recorded',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['description']}'),
                subtitle: Text(
                  '${row['expense_type_display']} · ${row['expense_date']}'
                  '${row['supplier_name']?.isEmpty ?? true ? '' : ' · ${row['supplier_name']}'}',
                ),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('₦${row['amount']}'),
                    Text(
                      '${row['payment_status_display']}',
                      style: TextStyle(
                        fontSize: 12,
                        color: row['payment_status'] == 'pending'
                            ? Theme.of(context).colorScheme.error
                            : Theme.of(context).hintColor,
                      ),
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

class _ExpenseSummary extends StatefulWidget {
  const _ExpenseSummary({required this.query, required this.reloadToken});

  final Map<String, String> query;
  final int reloadToken;

  @override
  State<_ExpenseSummary> createState() => _ExpenseSummaryState();
}

class _ExpenseSummaryState extends State<_ExpenseSummary> {
  Map<String, dynamic>? _totals;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(_ExpenseSummary old) {
    super.didUpdateWidget(old);
    if (old.query.toString() != widget.query.toString() ||
        old.reloadToken != widget.reloadToken) {
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final totals =
          await Api.get('/pharmacy/api/expenses/summary/', widget.query);
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
          Text('unpaid ₦${totals['pending']}'),
          Text(
            '₦${totals['total']}',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}

class NewExpenseScreen extends StatefulWidget {
  const NewExpenseScreen({super.key});

  @override
  State<NewExpenseScreen> createState() => _NewExpenseScreenState();
}

class _NewExpenseScreenState extends State<NewExpenseScreen> {
  String _type = 'operational';
  String _paymentStatus = 'pending';
  final _description = TextEditingController();
  final _amount = TextEditingController();
  final _reference = TextEditingController();
  DateTime _date = DateTime.now();
  bool _busy = false;

  Future<void> _submit() async {
    if (_description.text.trim().isEmpty || _amount.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Description and amount are required')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      await Api.post('/pharmacy/api/expenses/', {
        'expense_type': _type,
        'description': _description.text.trim(),
        'amount': _amount.text.trim(),
        'expense_date': _date.toIso8601String().split('T').first,
        'payment_status': _paymentStatus,
        'reference_number': _reference.text.trim(),
      });
      if (mounted) Navigator.pop(context, true);
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
      appBar: AppBar(title: const Text('Record expense')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          DropdownButtonFormField<String>(
            initialValue: _type,
            decoration: const InputDecoration(labelText: 'Type'),
            items: [
              for (final entry in _expenseTypes.entries)
                DropdownMenuItem(value: entry.key, child: Text(entry.value)),
            ],
            onChanged: (v) => setState(() => _type = v ?? 'operational'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _description,
            decoration: const InputDecoration(
              labelText: 'Description',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _amount,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Amount',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _reference,
            decoration: const InputDecoration(
              labelText: 'Invoice / reference',
              border: OutlineInputBorder(),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.event_outlined),
            title: Text('Dated ${_date.toIso8601String().split('T').first}'),
            onTap: () async {
              final picked = await showDatePicker(
                context: context,
                initialDate: _date,
                firstDate: DateTime(2020),
                lastDate: DateTime.now(),
              );
              if (picked != null) setState(() => _date = picked);
            },
          ),
          SwitchListTile(
            title: const Text('Already paid'),
            value: _paymentStatus == 'paid',
            onChanged: (on) =>
                setState(() => _paymentStatus = on ? 'paid' : 'pending'),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: const Text('Save expense'),
          ),
        ],
      ),
    );
  }
}
