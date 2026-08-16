import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';
import 'result_entry.dart';

const _requestStatuses = {
  '': 'All',
  'pending': 'Pending',
  'awaiting_payment': 'Awaiting payment',
  'payment_confirmed': 'Paid',
  'sample_collected': 'Sample collected',
  'processing': 'Processing',
  'completed': 'Completed',
};

/// Statuses a lab user moves a request through by hand.
const _nextStatuses = {
  'sample_collected': 'Mark sample collected',
  'processing': 'Mark processing',
  'cancelled': 'Cancel request',
};

class TestRequestListScreen extends StatefulWidget {
  const TestRequestListScreen({super.key});

  @override
  State<TestRequestListScreen> createState() => _TestRequestListScreenState();
}

class _TestRequestListScreenState extends State<TestRequestListScreen> {
  String _status = '';
  String _search = '';
  int _reloadToken = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Lab requests')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Patient name or ID',
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
                for (final entry in _requestStatuses.entries)
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
              path: '/laboratory/api/requests/',
              query: {'status': _status, 'search': _search},
              emptyMessage: 'No test requests',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['patient_name']} (${row['patient_number']})'),
                subtitle: Text(
                  '${(row['tests_detail'] as List).map((t) => t['name']).join(', ')}\n'
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
                      builder: (_) => TestRequestScreen(requestId: row['id'] as int),
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

class TestRequestScreen extends StatefulWidget {
  const TestRequestScreen({super.key, required this.requestId});

  final int requestId;

  @override
  State<TestRequestScreen> createState() => _TestRequestScreenState();
}

class _TestRequestScreenState extends State<TestRequestScreen> {
  Map<String, dynamic>? _request;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    try {
      final request =
          await Api.get('/laboratory/api/requests/${widget.requestId}/');
      setState(() {
        _request = request as Map<String, dynamic>;
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
      if (result is Map<String, dynamic>) setState(() => _request = result);
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

  Future<void> _verify(int resultId) async {
    await _act(() async {
      await Api.post('/laboratory/api/results/$resultId/verify/');
      return null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final request = _request;
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Test request')),
        body: Center(child: Text(_error!)),
      );
    }
    if (request == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final tests = (request['tests_detail'] as List).cast<Map<String, dynamic>>();
    final results = (request['results'] as List).cast<Map<String, dynamic>>();
    final resultsByTest = {for (final r in results) r['test'] as int: r};
    final canEnterResults = request['payment_verified'] == true &&
        request['can_process'] == true;

    return Scaffold(
      appBar: AppBar(
        title: Text('${request['patient_name']}'),
        actions: [
          PopupMenuButton<String>(
            enabled: !_busy,
            onSelected: (choice) => _act(() => Api.post(
                  '/laboratory/api/requests/${widget.requestId}/set_status/',
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
              title: Text('${request['status_display']} · ${request['priority']}'),
              subtitle: Text(
                'Requested by ${request['doctor_name']} on '
                '${request['request_date'].toString().split('T').first}',
              ),
              trailing: Text('₦${request['total_price']}'),
            ),
            if (request['blocked_reason']?.toString().isNotEmpty ?? false)
              ListTile(
                leading: Icon(
                  Icons.lock_outline,
                  color: Theme.of(context).colorScheme.error,
                ),
                title: Text('${request['blocked_reason']}'),
              )
            else if (request['payment_verified'] != true)
              ListTile(
                leading: Icon(
                  Icons.payments_outlined,
                  color: Theme.of(context).colorScheme.error,
                ),
                title: const Text('Payment pending — results cannot be entered'),
              ),
            const Divider(),
            for (final test in tests)
              _TestTile(
                test: test,
                result: resultsByTest[test['id'] as int],
                canEnterResults: canEnterResults && !_busy,
                onEnter: () async {
                  final saved = await Navigator.of(context).push<bool>(
                    MaterialPageRoute(
                      builder: (_) => ResultEntryScreen(
                        requestId: widget.requestId,
                        test: test,
                      ),
                    ),
                  );
                  if (saved == true) _reload();
                },
                onVerify: _verify,
              ),
            if (request['notes'] != null)
              ListTile(
                leading: const Icon(Icons.sticky_note_2_outlined),
                title: Text('${request['notes']}'),
              ),
          ],
        ),
      ),
    );
  }
}

class _TestTile extends StatelessWidget {
  const _TestTile({
    required this.test,
    required this.result,
    required this.canEnterResults,
    required this.onEnter,
    required this.onVerify,
  });

  final Map<String, dynamic> test;
  final Map<String, dynamic>? result;
  final bool canEnterResults;
  final VoidCallback onEnter;
  final void Function(int) onVerify;

  @override
  Widget build(BuildContext context) {
    final parameters =
        ((result?['parameters'] as List?) ?? const []).cast<Map<String, dynamic>>();
    final verified = result?['is_verified'] == true;

    return ExpansionTile(
      title: Text('${test['name']}'),
      subtitle: Text(
        result == null
            ? 'No result yet'
            : verified
                ? 'Verified by ${result!['verified_by_name']}'
                : 'Awaiting verification',
      ),
      leading: Icon(
        result == null
            ? Icons.hourglass_empty
            : verified
                ? Icons.verified
                : Icons.science_outlined,
        color: verified ? Colors.green : null,
      ),
      children: [
        for (final parameter in parameters)
          ListTile(
            dense: true,
            title: Text('${parameter['name']}'),
            subtitle: Text(
              'normal ${parameter['normal_range']?.isEmpty ?? true ? '—' : parameter['normal_range']}',
            ),
            trailing: Text(
              '${parameter['value']} ${parameter['unit'] ?? ''}',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: parameter['is_normal'] == false
                    ? Theme.of(context).colorScheme.error
                    : null,
              ),
            ),
          ),
        if (result?['notes'] != null)
          ListTile(dense: true, title: Text('${result!['notes']}')),
        Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              if (result == null && canEnterResults)
                FilledButton(
                  onPressed: onEnter,
                  child: const Text('Enter result'),
                ),
              if (result != null && !verified)
                FilledButton.tonal(
                  onPressed: () => onVerify(result!['id'] as int),
                  child: const Text('Verify'),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
