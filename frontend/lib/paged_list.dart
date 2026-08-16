import 'package:flutter/material.dart';

import 'api.dart';

/// Infinite-scrolling list over a DRF paginated endpoint
/// (`{count, next, previous, results}`).
class PagedList extends StatefulWidget {
  const PagedList({
    super.key,
    required this.path,
    required this.query,
    required this.itemBuilder,
    this.emptyMessage = 'Nothing found',
  });

  final String path;
  final Map<String, String> query;
  final Widget Function(BuildContext, Map<String, dynamic>) itemBuilder;
  final String emptyMessage;

  @override
  State<PagedList> createState() => _PagedListState();
}

class _PagedListState extends State<PagedList> {
  final _controller = ScrollController();
  final _items = <Map<String, dynamic>>[];
  String? _next;
  bool _loading = false;
  bool _first = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() {
      if (_controller.position.extentAfter < 400) _load();
    });
    _load();
  }

  @override
  void didUpdateWidget(PagedList old) {
    super.didUpdateWidget(old);
    if (old.path != widget.path ||
        old.query.toString() != widget.query.toString()) {
      _items.clear();
      _next = null;
      _first = true;
      _load();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (_loading || (!_first && _next == null)) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = _first
          ? await Api.get(widget.path, widget.query)
          : await Api.getUrl(_next!);
      final results = (data['results'] as List).cast<Map<String, dynamic>>();
      setState(() {
        _items.addAll(results);
        _next = data['next'] as String?;
        _first = false;
      });
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _refresh() async {
    _items.clear();
    _next = null;
    _first = true;
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null && _items.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!),
            TextButton(onPressed: _refresh, child: const Text('Retry')),
          ],
        ),
      );
    }
    if (_items.isEmpty) {
      return _loading
          ? const Center(child: CircularProgressIndicator())
          : Center(child: Text(widget.emptyMessage));
    }
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView.separated(
        controller: _controller,
        itemCount: _items.length + (_next == null ? 0 : 1),
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, i) => i < _items.length
            ? widget.itemBuilder(context, _items[i])
            : const Padding(
                padding: EdgeInsets.all(16),
                child: Center(child: CircularProgressIndicator()),
              ),
      ),
    );
  }
}
