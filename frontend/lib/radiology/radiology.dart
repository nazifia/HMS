import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';
import 'report_entry.dart';

const _orderStatuses = {
  '': 'All',
  'pending': 'Pending',
  'awaiting_payment': 'Awaiting payment',
  'payment_confirmed': 'Paid',
  'scheduled': 'Scheduled',
  'completed': 'Completed',
};

/// Statuses a radiographer moves an order through by hand.
const _nextStatuses = {
  'scheduled': 'Mark scheduled',
  'completed': 'Mark completed',
  'cancelled': 'Cancel order',
};

class RadiologyOrderListScreen extends StatefulWidget {
  const RadiologyOrderListScreen({super.key});

  @override
  State<RadiologyOrderListScreen> createState() =>
      _RadiologyOrderListScreenState();
}

class _RadiologyOrderListScreenState extends State<RadiologyOrderListScreen> {
  String _status = '';
  String _search = '';
  int _reloadToken = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Radiology orders')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Patient, ID or study',
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
                for (final entry in _orderStatuses.entries)
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
              key: ValueKey('$_status$_search$_reloadToken'),
              path: '/radiology/api/orders/',
              query: {'status': _status, 'search': _search},
              emptyMessage: 'No radiology orders',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['patient_name']} (${row['patient_number']})'),
                subtitle: Text(
                  '${row['test_name']}\n'
                  '${row['status_display']} · ${row['priority']}',
                ),
                isThreeLine: true,
                trailing: row['priority'] == 'normal'
                    ? null
                    : Icon(
                        Icons.priority_high,
                        color: Theme.of(context).colorScheme.error,
                      ),
                onTap: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) =>
                          RadiologyOrderScreen(orderId: row['id'] as int),
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

class RadiologyOrderScreen extends StatefulWidget {
  const RadiologyOrderScreen({super.key, required this.orderId});

  final int orderId;

  @override
  State<RadiologyOrderScreen> createState() => _RadiologyOrderScreenState();
}

class _RadiologyOrderScreenState extends State<RadiologyOrderScreen> {
  Map<String, dynamic>? _order;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    try {
      final order = await Api.get('/radiology/api/orders/${widget.orderId}/');
      if (!mounted) return;
      setState(() {
        _order = order as Map<String, dynamic>;
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _act(Future<dynamic> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
      await _reload();
    }
  }

  @override
  Widget build(BuildContext context) {
    final order = _order;
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Radiology order')),
        body: Center(child: Text(_error!)),
      );
    }
    if (order == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final result = order['result'] as Map<String, dynamic>?;
    final blocked = '${order['blocked_reason'] ?? ''}';

    return Scaffold(
      appBar: AppBar(
        title: Text('${order['patient_name']}'),
        actions: [
          PopupMenuButton<String>(
            enabled: !_busy,
            onSelected: (choice) => _act(() => Api.post(
                  '/radiology/api/orders/${widget.orderId}/set-status/',
                  {'status': choice},
                )),
            itemBuilder: (_) => [
              for (final entry in _nextStatuses.entries)
                PopupMenuItem(value: entry.key, child: Text(entry.value)),
            ],
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
              title: Text('${order['test_name']} · ${order['category_name']}'),
              subtitle: Text(
                '${order['status_display']} · ${order['priority']}\n'
                'Ordered by ${order['doctor_name']} on '
                '${order['order_date'].toString().split('T').first}',
              ),
              isThreeLine: true,
              trailing: Text('₦${order['test_price']}'),
            ),
            if (blocked.isNotEmpty)
              ListTile(
                leading: Icon(
                  Icons.lock_outline,
                  color: Theme.of(context).colorScheme.error,
                ),
                title: Text(blocked),
              ),
            if ('${order['clinical_information'] ?? ''}'.isNotEmpty)
              ListTile(
                leading: const Icon(Icons.notes),
                title: Text('${order['clinical_information']}'),
                subtitle: const Text('Clinical information'),
              ),
            const Divider(),
            if (result == null)
              const ListTile(
                leading: Icon(Icons.hourglass_empty),
                title: Text('No report yet'),
              )
            else
              _ReportCard(
                result: result,
                busy: _busy,
                onVerify: () => _act(() => Api.post(
                      '/radiology/api/results/${result['id']}/verify/',
                    )),
                onFinalize: () => _act(() => Api.post(
                      '/radiology/api/results/${result['id']}/finalize/',
                    )),
              ),
            if (order['can_add_result'] == true &&
                (result == null || result['is_verified'] != true))
              Padding(
                padding: const EdgeInsets.all(16),
                child: FilledButton(
                  onPressed: _busy
                      ? null
                      : () async {
                          final saved = await Navigator.of(context).push<bool>(
                            MaterialPageRoute(
                              builder: (_) => ReportEntryScreen(
                                orderId: widget.orderId,
                                order: order,
                                result: result,
                              ),
                            ),
                          );
                          if (saved == true) _reload();
                        },
                  child: Text(result == null ? 'Write report' : 'Edit report'),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ReportCard extends StatelessWidget {
  const _ReportCard({
    required this.result,
    required this.busy,
    required this.onVerify,
    required this.onFinalize,
  });

  final Map<String, dynamic> result;
  final bool busy;
  final VoidCallback onVerify;
  final VoidCallback onFinalize;

  @override
  Widget build(BuildContext context) {
    final verified = result['is_verified'] == true;
    final imageUrl = '${result['image_url'] ?? ''}';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ListTile(
          leading: Icon(
            verified ? Icons.verified : Icons.description_outlined,
            color: verified ? Colors.green : null,
          ),
          title: Text('${result['result_status_display']}'),
          subtitle: Text(
            verified
                ? 'Verified by ${result['verified_by_name']}'
                : 'Reported by ${result['performed_by_name']}',
          ),
          trailing: result['is_abnormal'] == true
              ? Icon(
                  Icons.warning_amber,
                  color: Theme.of(context).colorScheme.error,
                )
              : null,
        ),
        if (imageUrl.isNotEmpty)
          GestureDetector(
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => _ImageViewer(url: imageUrl)),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Image.network(
                imageUrl,
                height: 200,
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => const ListTile(
                  leading: Icon(Icons.broken_image_outlined),
                  title: Text('Study could not be loaded'),
                ),
              ),
            ),
          ),
        ListTile(
          title: const Text('Findings'),
          subtitle: Text('${result['findings']}'),
        ),
        ListTile(
          title: const Text('Impression'),
          subtitle: Text('${result['impression']}'),
        ),
        if ('${result['recommendations'] ?? ''}'.isNotEmpty)
          ListTile(
            title: const Text('Recommendations'),
            subtitle: Text('${result['recommendations']}'),
          ),
        if ('${result['verification_notes'] ?? ''}'.isNotEmpty)
          ListTile(
            title: const Text('Verification notes'),
            subtitle: Text('${result['verification_notes']}'),
          ),
        Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              if (!verified)
                FilledButton.tonal(
                  onPressed: busy ? null : onVerify,
                  child: const Text('Verify'),
                ),
              if (result['result_status'] == 'verified') ...[
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: busy ? null : onFinalize,
                  child: const Text('Finalize'),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

/// Full-screen study, pinch to zoom.
class _ImageViewer extends StatelessWidget {
  const _ImageViewer({required this.url});

  final String url;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(backgroundColor: Colors.black),
      body: Center(
        child: InteractiveViewer(
          maxScale: 5,
          child: Image.network(
            url,
            errorBuilder: (_, __, ___) => const Text(
              'Study could not be loaded',
              style: TextStyle(color: Colors.white),
            ),
          ),
        ),
      ),
    );
  }
}
