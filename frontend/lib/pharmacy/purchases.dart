import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

const _approvalFilters = {
  '': 'All',
  'draft': 'Draft',
  'pending': 'Awaiting approval',
  'approved': 'Approved',
  'rejected': 'Rejected',
};

const _paymentMethods = {
  'cash': 'Cash',
  'bank_transfer': 'Bank transfer',
  'cheque': 'Cheque',
  'credit_card': 'Credit card',
  'mobile_money': 'Mobile money',
  'other': 'Other',
};

class PurchaseListScreen extends StatefulWidget {
  const PurchaseListScreen({super.key});

  @override
  State<PurchaseListScreen> createState() => _PurchaseListScreenState();
}

class _PurchaseListScreenState extends State<PurchaseListScreen> {
  String _approval = '';
  String _search = '';
  int _reloadToken = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Purchase orders')),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final created = await Navigator.of(context).push<bool>(
            MaterialPageRoute(builder: (_) => const NewPurchaseScreen()),
          );
          if (created == true) setState(() => _reloadToken++);
        },
        child: const Icon(Icons.add),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Invoice number or supplier',
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
                for (final entry in _approvalFilters.entries)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: FilterChip(
                      label: Text(entry.value),
                      selected: _approval == entry.key,
                      onSelected: (_) => setState(() => _approval = entry.key),
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: PagedList(
              key: ValueKey('$_approval$_search$_reloadToken'),
              path: '/pharmacy/api/purchases/',
              query: {'approval_status': _approval, 'search': _search},
              emptyMessage: 'No purchase orders',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['invoice_number'] ?? 'Draft'} · ${row['supplier_name']}'),
                subtitle: Text(
                  '${row['approval_status_display']} · '
                  '${row['delivery_status_display']} · '
                  '${row['payment_status_display']}',
                ),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('₦${row['total_amount']}'),
                    if (Decimalish(row['outstanding']).isPositive)
                      Text(
                        'owing ₦${row['outstanding']}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                  ],
                ),
                onTap: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => PurchaseScreen(purchaseId: row['id'] as int),
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

class PurchaseScreen extends StatefulWidget {
  const PurchaseScreen({super.key, required this.purchaseId});

  final int purchaseId;

  @override
  State<PurchaseScreen> createState() => _PurchaseScreenState();
}

class _PurchaseScreenState extends State<PurchaseScreen> {
  Map<String, dynamic>? _purchase;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    try {
      final purchase = await Api.get('/pharmacy/api/purchases/${widget.purchaseId}/');
      setState(() {
        _purchase = purchase as Map<String, dynamic>;
        _error = null;
      });
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  Future<void> _act(Future<dynamic> Function() action) async {
    setState(() => _busy = true);
    try {
      final result = await action();
      final purchase = result is Map && result.containsKey('purchase')
          ? result['purchase']
          : result;
      if (purchase is Map<String, dynamic>) setState(() => _purchase = purchase);
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<String?> _askText(String title, String label) {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: InputDecoration(labelText: label),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  Future<void> _receiveDelivery() async {
    final items = (_purchase!['items'] as List).cast<Map<String, dynamic>>();
    final controllers = {
      for (final item in items)
        item['id'] as int:
            TextEditingController(text: '${item['quantity_outstanding']}'),
    };

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Receive delivery'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final item in items)
                TextField(
                  controller: controllers[item['id']],
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: '${item['medication_name']}',
                    helperText:
                        'ordered ${item['quantity']} · outstanding ${item['quantity_outstanding']}',
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
            child: const Text('Receive into stock'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    final quantities = <String, int>{};
    controllers.forEach((id, controller) {
      final value = int.tryParse(controller.text.trim());
      if (value != null) quantities['$id'] = value;
    });
    await _act(() => Api.post(
          '/pharmacy/api/purchases/${widget.purchaseId}/receive-delivery/',
          {'quantities': quantities},
        ));
  }

  Future<void> _pay() async {
    final amount = TextEditingController(text: '${_purchase!['outstanding']}');
    var method = 'cash';
    final reference = TextEditingController();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('Record payment'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: amount,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: 'Amount',
                  helperText: 'Outstanding ₦${_purchase!['outstanding']}',
                ),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: method,
                decoration: const InputDecoration(labelText: 'Method'),
                items: [
                  for (final entry in _paymentMethods.entries)
                    DropdownMenuItem(value: entry.key, child: Text(entry.value)),
                ],
                onChanged: (v) => setLocal(() => method = v ?? 'cash'),
              ),
              TextField(
                controller: reference,
                decoration: const InputDecoration(labelText: 'Reference'),
              ),
            ],
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

    await _act(() => Api.post('/pharmacy/api/purchases/${widget.purchaseId}/pay/', {
          'amount': amount.text.trim(),
          'payment_method': method,
          'reference': reference.text.trim(),
        }));
  }

  @override
  Widget build(BuildContext context) {
    final purchase = _purchase;
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Purchase')),
        body: Center(child: Text(_error!)),
      );
    }
    if (purchase == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final items = (purchase['items'] as List).cast<Map<String, dynamic>>();
    final payments = (purchase['payments'] as List).cast<Map<String, dynamic>>();
    final isDraft = purchase['approval_status'] == 'draft';

    return Scaffold(
      appBar: AppBar(
        title: Text('${purchase['invoice_number'] ?? 'Draft purchase'}'),
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
              title: Text('${purchase['supplier_name']}'),
              subtitle: Text(
                '${purchase['approval_status_display']} · '
                '${purchase['delivery_status_display']} · '
                '${purchase['payment_status_display']}',
              ),
              trailing: Text('₦${purchase['total_amount']}'),
            ),
            if ((purchase['approval_notes'] ?? '').toString().isNotEmpty)
              ListTile(
                dense: true,
                leading: const Icon(Icons.sticky_note_2_outlined),
                title: Text('${purchase['approval_notes']}'),
              ),
            const Divider(),
            for (final item in items)
              ListTile(
                title: Text(
                  '${item['medication_name']} ${item['medication_strength'] ?? ''}',
                ),
                subtitle: Text(
                  'ordered ${item['quantity']} · received ${item['quantity_received']} '
                  '· ₦${item['unit_price']} each · expires ${item['expiry_date']}',
                ),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('₦${item['total_price']}'),
                    if (isDraft)
                      IconButton(
                        icon: const Icon(Icons.delete_outline),
                        onPressed: _busy
                            ? null
                            : () => _act(() async {
                                  await Api.delete(
                                    '/pharmacy/api/purchase-items/${item['id']}/',
                                  );
                                  return Api.get(
                                    '/pharmacy/api/purchases/${widget.purchaseId}/',
                                  );
                                }),
                      ),
                  ],
                ),
              ),
            if (isDraft)
              ListTile(
                leading: const Icon(Icons.add),
                title: const Text('Add item'),
                onTap: _busy
                    ? null
                    : () async {
                        final added = await Navigator.of(context).push<bool>(
                          MaterialPageRoute(
                            builder: (_) =>
                                NewPurchaseItemScreen(purchaseId: widget.purchaseId),
                          ),
                        );
                        if (added == true) _reload();
                      },
              ),
            if (payments.isNotEmpty) ...[
              const Divider(),
              for (final payment in payments)
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.payments_outlined),
                  title: Text('₦${payment['amount']} · ${payment['payment_method_display']}'),
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
              trailing: Text('₦${purchase['amount_paid']}'),
            ),
            ListTile(
              dense: true,
              title: const Text('Outstanding'),
              trailing: Text(
                '₦${purchase['outstanding']}',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  if (isDraft)
                    _wide(FilledButton(
                      onPressed: _busy
                          ? null
                          : () => _act(() => Api.post(
                              '/pharmacy/api/purchases/${widget.purchaseId}/submit/')),
                      child: const Text('Submit for approval'),
                    )),
                  if (purchase['can_be_approved'] == true) ...[
                    _wide(FilledButton(
                      onPressed: _busy
                          ? null
                          : () async {
                              final notes = await _askText(
                                'Approve purchase', 'Notes (optional)');
                              if (notes == null) return;
                              await _act(() => Api.post(
                                    '/pharmacy/api/purchases/${widget.purchaseId}/approve/',
                                    {'notes': notes},
                                  ));
                            },
                      child: const Text('Approve'),
                    )),
                    const SizedBox(height: 8),
                    _wide(OutlinedButton(
                      onPressed: _busy
                          ? null
                          : () async {
                              final reason =
                                  await _askText('Reject purchase', 'Reason');
                              if (reason == null || reason.isEmpty) return;
                              await _act(() => Api.post(
                                    '/pharmacy/api/purchases/${widget.purchaseId}/reject/',
                                    {'reason': reason},
                                  ));
                            },
                      child: const Text('Reject'),
                    )),
                  ],
                  if (purchase['can_receive_delivery'] == true) ...[
                    const SizedBox(height: 8),
                    _wide(FilledButton.tonal(
                      onPressed: _busy ? null : _receiveDelivery,
                      child: const Text('Receive delivery'),
                    )),
                  ],
                  if (purchase['can_be_paid'] == true) ...[
                    const SizedBox(height: 8),
                    _wide(OutlinedButton.icon(
                      onPressed: _busy ? null : _pay,
                      icon: const Icon(Icons.payments_outlined),
                      label: const Text('Record payment'),
                    )),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _wide(Widget child) => SizedBox(width: double.infinity, child: child);
}

/// Add a supplier. The endpoint needs `pharmacy.add_supplier`, so this can
/// legitimately come back 403 for a pharmacist without procurement rights.
Future<Map<String, dynamic>?> createSupplier(BuildContext context) async {
  final name = TextEditingController();
  final phone = TextEditingController();
  final address = TextEditingController();
  final city = TextEditingController();
  final state = TextEditingController();

  final saved = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('New supplier'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              autofocus: true,
              decoration: const InputDecoration(labelText: 'Name'),
            ),
            TextField(
              controller: phone,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Phone'),
            ),
            TextField(
              controller: address,
              decoration: const InputDecoration(labelText: 'Address'),
            ),
            TextField(
              controller: city,
              decoration: const InputDecoration(labelText: 'City'),
            ),
            TextField(
              controller: state,
              decoration: const InputDecoration(labelText: 'State'),
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
          child: const Text('Create'),
        ),
      ],
    ),
  );
  if (saved != true || name.text.trim().isEmpty) return null;

  try {
    return await Api.post('/pharmacy/api/suppliers/', {
      'name': name.text.trim(),
      'phone_number': phone.text.trim(),
      'address': address.text.trim(),
      'city': city.text.trim(),
      'state': state.text.trim(),
    }) as Map<String, dynamic>;
  } on ApiException catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    }
    return null;
  }
}

class NewPurchaseScreen extends StatefulWidget {
  const NewPurchaseScreen({super.key});

  @override
  State<NewPurchaseScreen> createState() => _NewPurchaseScreenState();
}

class _NewPurchaseScreenState extends State<NewPurchaseScreen> {
  Map<String, dynamic>? _supplier;
  final _invoiceNumber = TextEditingController();
  final _notes = TextEditingController();
  bool _busy = false;

  Future<void> _pickSupplier() async {
    final data = await Api.get('/pharmacy/api/suppliers/');
    final list = (data is Map ? data['results'] : data) as List;
    if (!mounted) return;
    final chosen = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Supplier'),
        children: [
          for (final s in list.cast<Map<String, dynamic>>())
            SimpleDialogOption(
              onPressed: () => Navigator.pop(context, s),
              child: Text('${s['name']}'),
            ),
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, const {'id': -1}),
            child: const Text('+ New supplier'),
          ),
        ],
      ),
    );
    if (chosen == null) return;
    if (chosen['id'] == -1) {
      if (!mounted) return;
      final created = await createSupplier(context);
      if (created != null) setState(() => _supplier = created);
      return;
    }
    setState(() => _supplier = chosen);
  }

  Future<void> _submit() async {
    if (_supplier == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pick a supplier')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final purchase = await Api.post('/pharmacy/api/purchases/', {
        'supplier': _supplier!['id'],
        'purchase_date': DateTime.now().toIso8601String(),
        'invoice_number':
            _invoiceNumber.text.trim().isEmpty ? null : _invoiceNumber.text.trim(),
        'notes': _notes.text.trim(),
      });
      if (!mounted) return;
      Navigator.pop(context, true);
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PurchaseScreen(purchaseId: purchase['id'] as int),
        ),
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
    return Scaffold(
      appBar: AppBar(title: const Text('New purchase order')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ListTile(
            leading: const Icon(Icons.local_shipping_outlined),
            title: Text(_supplier?['name'] ?? 'Supplier'),
            onTap: _pickSupplier,
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _invoiceNumber,
            decoration: const InputDecoration(
              labelText: 'Supplier invoice number',
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
            child: const Text('Create draft'),
          ),
        ],
      ),
    );
  }
}

class NewPurchaseItemScreen extends StatefulWidget {
  const NewPurchaseItemScreen({super.key, required this.purchaseId});

  final int purchaseId;

  @override
  State<NewPurchaseItemScreen> createState() => _NewPurchaseItemScreenState();
}

class _NewPurchaseItemScreenState extends State<NewPurchaseItemScreen> {
  Map<String, dynamic>? _medication;
  final _quantity = TextEditingController(text: '1');
  final _unitPrice = TextEditingController();
  final _batch = TextEditingController();
  DateTime _expiry = DateTime.now().add(const Duration(days: 365));
  bool _busy = false;

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
    if (chosen != null) {
      setState(() {
        _medication = chosen;
        if (_unitPrice.text.isEmpty) _unitPrice.text = '${chosen['price']}';
      });
    }
  }

  Future<void> _submit() async {
    if (_medication == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pick a medication')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      await Api.post('/pharmacy/api/purchase-items/', {
        'purchase': widget.purchaseId,
        'medication': _medication!['id'],
        'quantity': int.tryParse(_quantity.text.trim()) ?? 0,
        'unit_price': _unitPrice.text.trim(),
        'batch_number': _batch.text.trim(),
        'expiry_date': _expiry.toIso8601String().split('T').first,
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
      appBar: AppBar(title: const Text('Add item')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
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
            controller: _unitPrice,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Unit cost',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _batch,
            decoration: const InputDecoration(
              labelText: 'Batch number',
              border: OutlineInputBorder(),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.event_outlined),
            title: Text('Expires ${_expiry.toIso8601String().split('T').first}'),
            onTap: () async {
              final picked = await showDatePicker(
                context: context,
                initialDate: _expiry,
                firstDate: DateTime.now(),
                lastDate: DateTime.now().add(const Duration(days: 3650)),
              );
              if (picked != null) setState(() => _expiry = picked);
            },
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: const Text('Add to purchase'),
          ),
        ],
      ),
    );
  }
}
