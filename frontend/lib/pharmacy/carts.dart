import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

const _cartStatusFilters = {
  '': 'All',
  'active': 'Active',
  'invoiced': 'Invoiced',
  'paid': 'Paid',
  'partially_dispensed': 'Partial',
  'completed': 'Completed',
};

class CartListScreen extends StatefulWidget {
  const CartListScreen({super.key});

  @override
  State<CartListScreen> createState() => _CartListScreenState();
}

class _CartListScreenState extends State<CartListScreen> {
  String _status = '';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Dispensing carts')),
      body: Column(
        children: [
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                for (final entry in _cartStatusFilters.entries)
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
            child: PagedList(
              path: '/pharmacy/api/carts/',
              query: {'status': _status},
              emptyMessage: 'No carts',
              itemBuilder: (context, cart) => ListTile(
                title: Text('Cart #${cart['id']} · ${cart['patient_name']}'),
                subtitle: Text(
                  '${cart['items'].length} item(s) · '
                  '${cart['dispensary_name']?.isEmpty ?? true ? 'no dispensary' : cart['dispensary_name']}',
                ),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(cart['status_display'] ?? ''),
                    Text(
                      '₦${cart['patient_payable']}',
                      style: const TextStyle(fontSize: 12),
                    ),
                  ],
                ),
                onTap: () => openCart(context, cart['id']),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

Future<void> openCart(BuildContext context, int cartId) {
  return Navigator.of(context).push(
    MaterialPageRoute(builder: (_) => CartScreen(cartId: cartId)),
  );
}

/// Create a cart for a prescription, or open the one that already exists.
Future<void> createCartForPrescription(
  BuildContext context,
  int prescriptionId,
) async {
  try {
    final result = await Api.post('/pharmacy/api/carts/', {
      'prescription': prescriptionId,
    });
    if (!context.mounted) return;
    await openCart(context, result['cart']['id']);
  } on ApiException catch (e) {
    final existing = e.body is Map ? e.body['cart'] : null;
    if (!context.mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(e.message)));
    if (existing != null) await openCart(context, existing['id']);
  }
}

class CartScreen extends StatefulWidget {
  const CartScreen({super.key, required this.cartId});

  final int cartId;

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  Map<String, dynamic>? _cart;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    try {
      final cart = await Api.get('/pharmacy/api/carts/${widget.cartId}/');
      setState(() {
        _cart = cart as Map<String, dynamic>;
        _error = null;
      });
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  /// Runs a cart action, shows whatever the server says, and refreshes.
  Future<void> _act(Future<dynamic> Function() action) async {
    setState(() => _busy = true);
    try {
      final result = await action();
      final cart = result is Map && result.containsKey('cart')
          ? result['cart']
          : result;
      if (cart is Map<String, dynamic>) setState(() => _cart = cart);
      if (result is Map && result['notes'] is List) {
        for (final note in result['notes']) {
          if (mounted) {
            ScaffoldMessenger.of(context)
                .showSnackBar(SnackBar(content: Text('$note')));
          }
        }
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickDispensary() async {
    final data = await Api.get('/pharmacy/api/dispensaries/');
    final list = (data is Map ? data['results'] : data) as List;
    if (!mounted) return;
    final chosen = await showDialog<Map<String, dynamic>>(
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
    if (chosen == null) return;
    await _act(() => Api.post(
          '/pharmacy/api/carts/${widget.cartId}/dispensary/',
          {'dispensary': chosen['id']},
        ));
  }

  Future<void> _editQuantity(Map<String, dynamic> item) async {
    final controller = TextEditingController(text: '${item['quantity']}');
    final value = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('${item['medication']['name']}'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          autofocus: true,
          decoration: InputDecoration(
            labelText: 'Quantity',
            helperText: 'In stock: ${item['available_stock']}',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    final quantity = int.tryParse(value ?? '');
    if (quantity == null) return;
    await _act(() => Api.patch(
          '/pharmacy/api/cart-items/${item['id']}/',
          {'quantity': quantity},
        ));
  }

  Future<void> _payFromWallet() async {
    final wallet = await Api.get('/pharmacy/api/carts/${widget.cartId}/wallet/');
    final balance = double.tryParse('${wallet['balance']}') ?? 0;
    final due = double.tryParse('${wallet['due']}') ?? 0;
    final short = balance < due;
    if (!mounted) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Pay from wallet'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Wallet balance: ₦${wallet['balance']}'),
            Text('Amount due: ₦${wallet['due']}'),
            if (short) ...[
              const SizedBox(height: 12),
              Text(
                'Short by ₦${(due - balance).toStringAsFixed(2)}. '
                'Confirming will overdraw the wallet.',
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(short ? 'Overdraw and pay' : 'Pay'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    await _act(() => Api.post(
          '/pharmacy/api/carts/${widget.cartId}/pay-from-wallet/',
          {'allow_negative': short},
        ));
  }

  Future<void> _substitute(Map<String, dynamic> item) async {
    final alternatives = await Api.get(
      '/pharmacy/api/cart-items/${item['id']}/alternatives/',
    ) as List;
    if (!mounted) return;
    if (alternatives.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No other medication in stock at this dispensary'),
        ),
      );
      return;
    }

    final chosen = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Substitute with'),
        children: [
          for (final med in alternatives.cast<Map<String, dynamic>>())
            SimpleDialogOption(
              onPressed: () => Navigator.pop(context, med),
              child: Text(
                '${med['name']} ${med['strength'] ?? ''} · '
                'stock ${med['stock']} · ₦${med['price']}',
              ),
            ),
        ],
      ),
    );
    if (chosen == null || !mounted) return;

    final controller = TextEditingController();
    final reason = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Substitute with ${chosen['name']}'),
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
            child: const Text('Substitute'),
          ),
        ],
      ),
    );
    if (reason == null || reason.isEmpty) return;

    await _act(() => Api.post(
          '/pharmacy/api/cart-items/${item['id']}/substitute/',
          {'medication': chosen['id'], 'reason': reason},
        ));
  }

  Future<void> _dispense() async {
    final items = (_cart!['items'] as List).cast<Map<String, dynamic>>();
    final controllers = {
      for (final item in items)
        item['id'] as int:
            TextEditingController(text: '${item['available_now']}'),
    };

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Dispense'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final item in items)
                TextField(
                  controller: controllers[item['id']],
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: '${item['medication']['name']}',
                    helperText:
                        'remaining ${item['remaining']} · available now ${item['available_now']}',
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
            child: const Text('Dispense'),
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
          '/pharmacy/api/carts/${widget.cartId}/dispense/',
          {'quantities': quantities},
        ));
  }

  @override
  Widget build(BuildContext context) {
    final cart = _cart;
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Cart')),
        body: Center(child: Text(_error!)),
      );
    }
    if (cart == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final items = (cart['items'] as List).cast<Map<String, dynamic>>();
    final editable = cart['status'] == 'active' || cart['status'] == 'invoiced';
    final progress = cart['progress'] as Map<String, dynamic>;

    return Scaffold(
      appBar: AppBar(
        title: Text('Cart #${cart['id']}'),
        actions: [
          if (cart['status'] != 'cancelled' && cart['status'] != 'completed')
            IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Cancel cart',
              onPressed: _busy
                  ? null
                  : () => _act(() =>
                      Api.post('/pharmacy/api/carts/${widget.cartId}/cancel/')),
            ),
        ],
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
              title: Text('${cart['patient_name']} (${cart['patient_number']})'),
              subtitle: Text(
                '${cart['status_display']}'
                '${cart['invoice_status']?.isEmpty ?? true ? '' : ' · invoice ${cart['invoice_status']}'}',
              ),
            ),
            ListTile(
              leading: const Icon(Icons.store_outlined),
              title: Text(
                cart['dispensary_name']?.isEmpty ?? true
                    ? 'No dispensary selected'
                    : '${cart['dispensary_name']}',
              ),
              trailing: editable ? const Icon(Icons.edit) : null,
              onTap: editable && !_busy ? _pickDispensary : null,
            ),
            if (progress['percentage'] != 0)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: LinearProgressIndicator(
                  value: (progress['percentage'] as int) / 100,
                ),
              ),
            const Divider(),
            for (final item in items)
              ListTile(
                title: Text(
                  '${item['medication']['name']} ${item['medication']['strength'] ?? ''}',
                ),
                subtitle: Text(
                  'qty ${item['quantity']} · dispensed ${item['quantity_dispensed']} · '
                  'stock ${item['available_stock']}'
                  '${item['is_substituted'] == true ? ' · substituted: ${item['substitute_reason']}' : ''}',
                ),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('₦${item['subtotal']}'),
                    if (editable)
                      PopupMenuButton<String>(
                        enabled: !_busy,
                        onSelected: (choice) => switch (choice) {
                          'quantity' => _editQuantity(item),
                          'substitute' => _substitute(item),
                          'unsubstitute' => _act(() => Api.post(
                              '/pharmacy/api/cart-items/${item['id']}/remove-substitution/')),
                          _ => _act(() => Api.delete(
                              '/pharmacy/api/cart-items/${item['id']}/')),
                        },
                        itemBuilder: (_) => [
                          const PopupMenuItem(
                            value: 'quantity',
                            child: Text('Edit quantity'),
                          ),
                          if (item['is_substituted'] == true)
                            const PopupMenuItem(
                              value: 'unsubstitute',
                              child: Text('Undo substitution'),
                            )
                          else
                            const PopupMenuItem(
                              value: 'substitute',
                              child: Text('Substitute'),
                            ),
                          const PopupMenuItem(
                            value: 'remove',
                            child: Text('Remove from cart'),
                          ),
                        ],
                      ),
                  ],
                ),
                onTap: editable && !_busy ? () => _editQuantity(item) : null,
              ),
            const Divider(),
            _total('Subtotal', cart['subtotal']),
            if (Decimalish(cart['nhia_coverage']).isPositive)
              _total('NHIA covers (90%)', cart['nhia_coverage']),
            _total('Patient pays', cart['patient_payable'], bold: true),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  if (cart['status'] == 'active')
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: _busy
                            ? null
                            : () => _act(() => Api.post(
                                '/pharmacy/api/carts/${widget.cartId}/invoice/')),
                        child: const Text('Generate invoice'),
                      ),
                    ),
                  if (cart['invoice_status'] != 'paid' &&
                      cart['status'] != 'cancelled' &&
                      cart['status'] != 'completed') ...[
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: _busy ? null : _payFromWallet,
                        icon: const Icon(Icons.account_balance_wallet_outlined),
                        label: const Text('Pay from patient wallet'),
                      ),
                    ),
                  ],
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.tonal(
                      onPressed:
                          cart['can_dispense'] == true && !_busy ? _dispense : null,
                      child: Text(
                        cart['can_dispense'] == true
                            ? 'Dispense'
                            : '${cart['dispense_blocked_reason']}',
                        textAlign: TextAlign.center,
                      ),
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

  Widget _total(String label, Object? value, {bool bold = false}) {
    final style = bold ? const TextStyle(fontWeight: FontWeight.bold) : null;
    return ListTile(
      dense: true,
      title: Text(label, style: style),
      trailing: Text('₦$value', style: style),
    );
  }
}
