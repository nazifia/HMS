import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

const _paymentMethods = {
  'cash': 'Cash',
  'bank_transfer': 'Bank transfer',
  'pos': 'POS',
  'cheque': 'Cheque',
};

class WalletScreen extends StatefulWidget {
  const WalletScreen({super.key, required this.patient});

  final Map<String, dynamic> patient;

  @override
  State<WalletScreen> createState() => _WalletScreenState();
}

class _WalletScreenState extends State<WalletScreen> {
  Map<String, dynamic>? _summary;
  String? _error;
  int _reloadToken = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final summary =
          await Api.get('/patients/api/patients/${widget.patient['id']}/wallet/');
      if (mounted) {
        setState(() {
          _summary = summary as Map<String, dynamic>;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _fund() async {
    final amount = TextEditingController();
    final description = TextEditingController();
    var method = 'cash';
    var applyToOutstanding = false;
    final owing =
        double.tryParse('${_summary?['outstanding']?['total'] ?? 0}') ?? 0;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('Add funds'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: amount,
                  autofocus: true,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Amount'),
                ),
                DropdownButtonFormField<String>(
                  initialValue: method,
                  decoration: const InputDecoration(labelText: 'Payment method'),
                  items: [
                    for (final entry in _paymentMethods.entries)
                      DropdownMenuItem(
                        value: entry.key,
                        child: Text(entry.value),
                      ),
                  ],
                  onChanged: (v) => setLocal(() => method = v ?? 'cash'),
                ),
                TextField(
                  controller: description,
                  decoration: const InputDecoration(labelText: 'Description'),
                ),
                if (owing > 0)
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('Settle ₦$owing outstanding'),
                    value: applyToOutstanding,
                    onChanged: (v) =>
                        setLocal(() => applyToOutstanding = v ?? false),
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Add funds'),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true) return;

    try {
      final result = await Api.post(
        '/patients/api/patients/${widget.patient['id']}/fund/',
        {
          'amount': amount.text.trim(),
          'payment_method': method,
          'description': description.text.trim(),
          'apply_to_outstanding': applyToOutstanding,
        },
      );
      if (!mounted) return;
      setState(() {
        _summary = {
          'wallet': result['wallet'],
          'outstanding': {
            ..._summary?['outstanding'] ?? {},
            'total': result['outstanding'],
          },
        };
        _reloadToken++;
      });
      await _load();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final summary = _summary;
    return Scaffold(
      appBar: AppBar(title: Text('Wallet · ${widget.patient['full_name']}')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _fund,
        icon: const Icon(Icons.add),
        label: const Text('Add funds'),
      ),
      body: _error != null
          ? Center(child: Text(_error!))
          : summary == null
              ? const Center(child: CircularProgressIndicator())
              : Column(
                  children: [
                    ListTile(
                      title: const Text('Balance'),
                      trailing: Text(
                        '₦${summary['wallet']['balance']}',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    if (Decimalish(summary['outstanding']['total']).isPositive)
                      ListTile(
                        title: const Text('Outstanding'),
                        subtitle: Text(
                          'admissions ₦${summary['outstanding']['admissions']} · '
                          'invoices ₦${summary['outstanding']['invoices']}',
                        ),
                        trailing: Text(
                          '₦${summary['outstanding']['total']}',
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    const Divider(height: 1),
                    Expanded(
                      child: PagedList(
                        key: ValueKey(_reloadToken),
                        path:
                            '/patients/api/patients/${widget.patient['id']}/transactions/',
                        query: const {},
                        emptyMessage: 'No transactions yet',
                        itemBuilder: (context, row) => ListTile(
                          title: Text('${row['description']}'),
                          subtitle: Text(
                            '${row['transaction_type_display']} · '
                            '${row['created_at'].toString().split('T').first}'
                            '${row['created_by_name']?.isEmpty ?? true ? '' : ' · ${row['created_by_name']}'}',
                          ),
                          trailing: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Text('₦${row['amount']}'),
                              Text(
                                'bal ₦${row['balance_after']}',
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
