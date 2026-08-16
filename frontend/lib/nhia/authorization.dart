import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

/// The desk office: what is waiting on an authorization code, and the codes
/// already issued.
class AuthorizationScreen extends StatefulWidget {
  const AuthorizationScreen({super.key});

  @override
  State<AuthorizationScreen> createState() => _AuthorizationScreenState();
}

class _AuthorizationScreenState extends State<AuthorizationScreen> {
  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('NHIA authorization'),
          actions: [
            IconButton(
              icon: const Icon(Icons.qr_code_scanner),
              tooltip: 'Verify a code',
              onPressed: () => showDialog(
                context: context,
                builder: (_) => const _VerifyDialog(),
              ),
            ),
          ],
          bottom: const TabBar(tabs: [
            Tab(text: 'Waiting'),
            Tab(text: 'Codes'),
          ]),
        ),
        body: const TabBarView(
          children: [PendingQueueScreen(), AuthorizationCodeListScreen()],
        ),
      ),
    );
  }
}

/// Everything across the hospital waiting on a code, newest first.
class PendingQueueScreen extends StatefulWidget {
  const PendingQueueScreen({super.key});

  @override
  State<PendingQueueScreen> createState() => _PendingQueueScreenState();
}

class _PendingQueueScreenState extends State<PendingQueueScreen> {
  static const _kinds = {
    '': 'All',
    'consultation': 'Consultations',
    'referral': 'Referrals',
    'prescription': 'Prescriptions',
    'laboratory': 'Lab',
    'radiology': 'Radiology',
    'surgery': 'Surgery',
  };

  String _kind = '';
  Map<String, dynamic>? _data;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    try {
      final data = await Api.get('/nhia/api/pending/', {'kind': _kind});
      if (!mounted) return;
      setState(() {
        _data = data as Map<String, dynamic>;
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _authorize(Map<String, dynamic> row) async {
    final amount = TextEditingController(text: '${row['estimated_amount']}');
    final notes = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Authorize ${row['kind_display'].toString().toLowerCase()}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('${row['patient_name']} · ${row['description']}'),
            const SizedBox(height: 12),
            TextField(
              controller: amount,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'Amount covered (₦)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: notes,
              decoration: const InputDecoration(
                labelText: 'Notes',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Issue code'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    setState(() => _busy = true);
    try {
      final code = await Api.post(
        '/nhia/api/pending/${row['kind']}/${row['id']}/authorize/',
        {'amount': amount.text.trim(), 'notes': notes.text.trim()},
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Code ${code['code']} issued')),
        );
      }
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
    final data = _data;
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!),
            TextButton(onPressed: _reload, child: const Text('Retry')),
          ],
        ),
      );
    }
    if (data == null) {
      return const Center(child: CircularProgressIndicator());
    }

    final counts = data['counts'] as Map<String, dynamic>;
    final rows = (data['results'] as List).cast<Map<String, dynamic>>();

    return Column(
      children: [
        if (_busy) const LinearProgressIndicator(),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            children: [
              for (final entry in _kinds.entries)
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: FilterChip(
                    label: Text(
                      entry.key.isEmpty
                          ? '${entry.value} (${counts['total']})'
                          : '${entry.value} (${counts[entry.key] ?? 0})',
                    ),
                    selected: _kind == entry.key,
                    onSelected: (_) {
                      setState(() => _kind = entry.key);
                      _reload();
                    },
                  ),
                ),
            ],
          ),
        ),
        Expanded(
          child: rows.isEmpty
              ? const Center(child: Text('Nothing waiting on authorization'))
              : RefreshIndicator(
                  onRefresh: _reload,
                  child: ListView.separated(
                    itemCount: rows.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, i) {
                      final row = rows[i];
                      return ListTile(
                        title: Text(
                          '${row['patient_name']} (${row['patient_number']})',
                        ),
                        subtitle: Text(
                          '${row['kind_display']} · ${row['description']}\n'
                          'Estimated ₦${row['estimated_amount']}',
                        ),
                        isThreeLine: true,
                        trailing: FilledButton.tonal(
                          onPressed: _busy ? null : () => _authorize(row),
                          child: const Text('Authorize'),
                        ),
                      );
                    },
                  ),
                ),
        ),
      ],
    );
  }
}

/// Codes already issued, with cancellation.
class AuthorizationCodeListScreen extends StatefulWidget {
  const AuthorizationCodeListScreen({super.key});

  @override
  State<AuthorizationCodeListScreen> createState() =>
      _AuthorizationCodeListScreenState();
}

class _AuthorizationCodeListScreenState
    extends State<AuthorizationCodeListScreen> {
  static const _statuses = {
    '': 'All',
    'active': 'Active',
    'used': 'Used',
    'expired': 'Expired',
    'cancelled': 'Cancelled',
  };

  String _status = 'active';
  String _search = '';
  int _reloadToken = 0;

  Future<void> _cancel(Map<String, dynamic> code) async {
    try {
      await Api.post('/nhia/api/authorization-codes/${code['id']}/cancel/');
      setState(() => _reloadToken++);
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
          child: TextField(
            textInputAction: TextInputAction.search,
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Code, patient name or ID',
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
              for (final entry in _statuses.entries)
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
            path: '/nhia/api/authorization-codes/',
            query: {'status': _status, 'search': _search},
            emptyMessage: 'No authorization codes',
            itemBuilder: (context, row) => ListTile(
              title: Text('${row['code']}'),
              subtitle: Text(
                '${row['patient_name']} · ${row['service_type_display']}\n'
                '₦${row['amount']} · ${row['status_display']} · '
                'expires ${row['expiry_date']}',
              ),
              isThreeLine: true,
              trailing: row['status'] == 'active'
                  ? IconButton(
                      icon: const Icon(Icons.block),
                      tooltip: 'Cancel code',
                      onPressed: () => _cancel(row),
                    )
                  : null,
            ),
          ),
        ),
      ],
    );
  }
}

/// Check a code the patient is holding before starting work.
class _VerifyDialog extends StatefulWidget {
  const _VerifyDialog();

  @override
  State<_VerifyDialog> createState() => _VerifyDialogState();
}

class _VerifyDialogState extends State<_VerifyDialog> {
  final _code = TextEditingController();
  Map<String, dynamic>? _result;
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final data = await Api.get(
        '/nhia/api/authorization-codes/verify/',
        {'code': _code.text.trim()},
      );
      setState(() => _result = data as Map<String, dynamic>);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    return AlertDialog(
      title: const Text('Verify authorization code'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _code,
            autofocus: true,
            textCapitalization: TextCapitalization.characters,
            decoration: const InputDecoration(
              labelText: 'Code',
              border: OutlineInputBorder(),
            ),
            onSubmitted: (_) => _verify(),
          ),
          if (_busy)
            const Padding(
              padding: EdgeInsets.only(top: 16),
              child: CircularProgressIndicator(),
            ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          if (result != null)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Column(
                children: [
                  Icon(
                    result['valid'] == true ? Icons.check_circle : Icons.cancel,
                    color: result['valid'] == true
                        ? Colors.green
                        : Theme.of(context).colorScheme.error,
                    size: 40,
                  ),
                  const SizedBox(height: 8),
                  Text('${result['message']}'),
                  if (result['code'] != null)
                    Text(
                      '${result['code']['patient_name']} · '
                      '₦${result['code']['amount']}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                ],
              ),
            ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Close'),
        ),
        FilledButton(onPressed: _busy ? null : _verify, child: const Text('Verify')),
      ],
    );
  }
}
