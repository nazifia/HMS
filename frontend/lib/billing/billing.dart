import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

const _invoiceStatuses = {
  '': 'All',
  'pending': 'Pending',
  'partially_paid': 'Part paid',
  'paid': 'Paid',
  'overdue': 'Overdue',
  'cancelled': 'Cancelled',
};

const _paymentMethods = {
  'cash': 'Cash',
  'bank_transfer': 'Bank transfer',
  'debit_card': 'Debit card',
  'credit_card': 'Credit card',
  'insurance': 'Insurance',
  'other': 'Other',
};

class InvoiceListScreen extends StatefulWidget {
  const InvoiceListScreen({super.key});

  @override
  State<InvoiceListScreen> createState() => _InvoiceListScreenState();
}

class _InvoiceListScreenState extends State<InvoiceListScreen> {
  String _status = '';
  String _search = '';
  bool _unpaidOnly = false;
  int _reloadToken = 0;

  Map<String, String> get _query => {
        'status': _status,
        'search': _search,
        'unpaid': _unpaidOnly ? 'true' : '',
      };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Invoices')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Invoice number, patient name or ID',
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
                FilterChip(
                  label: const Text('Owing'),
                  selected: _unpaidOnly,
                  onSelected: (on) => setState(() => _unpaidOnly = on),
                ),
                const SizedBox(width: 12),
                for (final entry in _invoiceStatuses.entries)
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
          _CashierSummary(query: _query, reloadToken: _reloadToken),
          const Divider(height: 1),
          Expanded(
            child: PagedList(
              key: ValueKey('$_status$_search$_unpaidOnly$_reloadToken'),
              path: '/billing/api/invoices/',
              query: _query,
              emptyMessage: 'No invoices match',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['invoice_number']} · ${row['patient_name']}'),
                subtitle: Text(
                  '${row['service_details'] ?? row['source_app_display']}\n'
                  '${row['status_display']} · due ${row['due_date']}',
                ),
                isThreeLine: true,
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('₦${row['total_amount']}'),
                    if (Decimalish(row['balance']).isPositive)
                      Text(
                        'owing ₦${row['balance']}',
                        style: TextStyle(
                          fontSize: 12,
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                  ],
                ),
                onTap: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => InvoiceScreen(invoiceId: row['id'] as int),
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

class _CashierSummary extends StatefulWidget {
  const _CashierSummary({required this.query, required this.reloadToken});

  final Map<String, String> query;
  final int reloadToken;

  @override
  State<_CashierSummary> createState() => _CashierSummaryState();
}

class _CashierSummaryState extends State<_CashierSummary> {
  Map<String, dynamic>? _totals;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(_CashierSummary old) {
    super.didUpdateWidget(old);
    if (old.query.toString() != widget.query.toString() ||
        old.reloadToken != widget.reloadToken) {
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final totals =
          await Api.get('/billing/api/invoices/summary/', widget.query);
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
          Text('${totals['invoices']} invoices'),
          Text('owing ₦${totals['outstanding']}'),
          Text(
            'today ₦${totals['collected_today']}',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}

class InvoiceScreen extends StatefulWidget {
  const InvoiceScreen({super.key, required this.invoiceId});

  final int invoiceId;

  @override
  State<InvoiceScreen> createState() => _InvoiceScreenState();
}

class _InvoiceScreenState extends State<InvoiceScreen> {
  Map<String, dynamic>? _invoice;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    try {
      final invoice = await Api.get('/billing/api/invoices/${widget.invoiceId}/');
      setState(() {
        _invoice = invoice as Map<String, dynamic>;
        _error = null;
      });
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  Future<void> _pay() async {
    final invoice = _invoice!;
    final balance = double.tryParse('${invoice['balance']}') ?? 0;
    final walletBalance =
        double.tryParse('${invoice['wallet_balance'] ?? 0}') ?? 0;

    final amount = TextEditingController(text: '${invoice['balance']}');
    final reference = TextEditingController();
    var method = 'cash';
    var fromWallet = false;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('Record payment'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: amount,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(
                    labelText: 'Amount',
                    helperText: 'Balance ₦${invoice['balance']}',
                  ),
                ),
                if (invoice['wallet_balance'] != null)
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Pay from patient wallet'),
                    subtitle: Text('Wallet holds ₦${invoice['wallet_balance']}'),
                    value: fromWallet,
                    onChanged: (on) => setLocal(() => fromWallet = on),
                  ),
                if (!fromWallet)
                  DropdownButtonFormField<String>(
                    initialValue: method,
                    decoration: const InputDecoration(labelText: 'Method'),
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
                  controller: reference,
                  decoration: const InputDecoration(labelText: 'Reference'),
                ),
                if (fromWallet && walletBalance < balance)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      'Wallet is short by '
                      '₦${(balance - walletBalance).toStringAsFixed(2)}.',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
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
              child: const Text('Record'),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true) return;

    setState(() => _busy = true);
    try {
      final result = await Api.post(
        '/billing/api/invoices/${widget.invoiceId}/pay/',
        {
          'amount': amount.text.trim(),
          'payment_source': fromWallet ? 'patient_wallet' : 'billing_office',
          'payment_method': fromWallet ? 'wallet' : method,
          'transaction_id': reference.text.trim(),
        },
      );
      if (!mounted) return;
      setState(() => _invoice = result['invoice'] as Map<String, dynamic>);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${result['message']}')),
      );
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
    final invoice = _invoice;
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Invoice')),
        body: Center(child: Text(_error!)),
      );
    }
    if (invoice == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final items = (invoice['items'] as List).cast<Map<String, dynamic>>();
    final payments = (invoice['payments'] as List).cast<Map<String, dynamic>>();
    final owing = Decimalish(invoice['balance']).isPositive;

    return Scaffold(
      appBar: AppBar(
        title: Text('${invoice['invoice_number']}'),
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
              title: Text('${invoice['patient_name']} (${invoice['patient_number']})'),
              subtitle: Text(
                '${invoice['status_display']} · ${invoice['source_app_display']} · '
                'due ${invoice['due_date']}',
              ),
              trailing: Text('₦${invoice['total_amount']}'),
            ),
            const Divider(),
            for (final item in items)
              ListTile(
                dense: true,
                title: Text(
                  '${item['service_name']?.isEmpty ?? true ? item['description'] : item['service_name']}',
                ),
                subtitle: Text('${item['quantity']} × ₦${item['unit_price']}'),
                trailing: Text('₦${item['total_amount']}'),
              ),
            if (payments.isNotEmpty) ...[
              const Divider(),
              for (final payment in payments)
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.payments_outlined),
                  title: Text(
                    '₦${payment['amount']} · ${payment['payment_method_display']}',
                  ),
                  subtitle: Text(
                    '${payment['payment_date'].toString().split('T').first}'
                    '${payment['received_by_name']?.isEmpty ?? true ? '' : ' · ${payment['received_by_name']}'}',
                  ),
                ),
            ],
            const Divider(),
            ListTile(
              dense: true,
              title: const Text('Paid'),
              trailing: Text('₦${invoice['amount_paid']}'),
            ),
            ListTile(
              dense: true,
              title: const Text('Balance'),
              trailing: Text(
                '₦${invoice['balance']}',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: owing ? Theme.of(context).colorScheme.error : null,
                ),
              ),
            ),
            if (owing)
              Padding(
                padding: const EdgeInsets.all(16),
                child: SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: _busy ? null : _pay,
                    icon: const Icon(Icons.payments_outlined),
                    label: const Text('Record payment'),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
