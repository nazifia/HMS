import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';
import 'record_form.dart';

/// The eighteen specialty modules, listed from the server so a nineteenth
/// needs no app change.
class SpecialtyModulesScreen extends StatefulWidget {
  const SpecialtyModulesScreen({super.key});

  @override
  State<SpecialtyModulesScreen> createState() => _SpecialtyModulesScreenState();
}

class _SpecialtyModulesScreenState extends State<SpecialtyModulesScreen> {
  List<Map<String, dynamic>>? _modules;
  String? _error;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    try {
      final data = await Api.get('/api/specialty/modules/');
      if (!mounted) return;
      setState(() {
        _modules = (data as List).cast<Map<String, dynamic>>();
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final modules = _modules;
    return Scaffold(
      appBar: AppBar(title: const Text('Specialty clinics')),
      body: _error != null
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(_error!),
                  TextButton(onPressed: _reload, child: const Text('Retry')),
                ],
              ),
            )
          : modules == null
              ? const Center(child: CircularProgressIndicator())
              : ListView.separated(
                  itemCount: modules.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, i) {
                    final module = modules[i];
                    return ListTile(
                      leading: const Icon(Icons.local_hospital_outlined),
                      title: Text('${module['label']}'),
                      subtitle: module['has_clinical_notes'] == true
                          ? const Text('Records and clerking notes')
                          : const Text('Records'),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => SpecialtyRecordListScreen(
                            kind: '${module['kind']}',
                            label: '${module['label']}',
                          ),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}

/// Records for one module.
class SpecialtyRecordListScreen extends StatefulWidget {
  const SpecialtyRecordListScreen({
    super.key,
    required this.kind,
    required this.label,
  });

  final String kind;
  final String label;

  @override
  State<SpecialtyRecordListScreen> createState() =>
      _SpecialtyRecordListScreenState();
}

class _SpecialtyRecordListScreenState extends State<SpecialtyRecordListScreen> {
  String _search = '';
  int _reloadToken = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.label)),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final saved = await Navigator.of(context).push<bool>(
            MaterialPageRoute(
              builder: (_) => SpecialtyRecordFormScreen(
                kind: widget.kind,
                label: widget.label,
              ),
            ),
          );
          if (saved == true) setState(() => _reloadToken++);
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
                hintText: 'Patient name or ID',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onSubmitted: (v) => setState(() => _search = v.trim()),
            ),
          ),
          Expanded(
            child: PagedList(
              key: ValueKey('$_search$_reloadToken'),
              path: '/api/specialty/${widget.kind}/records/',
              query: {'search': _search},
              emptyMessage: 'No ${widget.label.toLowerCase()} records',
              itemBuilder: (context, row) => ListTile(
                title: Text('${row['patient_name']} (${row['patient_number']})'),
                subtitle: Text(
                  [
                    if ('${row['diagnosis'] ?? ''}'.isNotEmpty)
                      '${row['diagnosis']}',
                    if ('${row['doctor_name'] ?? ''}'.isNotEmpty)
                      'Seen by ${row['doctor_name']}',
                  ].join('\n'),
                ),
                onTap: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => SpecialtyRecordFormScreen(
                        kind: widget.kind,
                        label: widget.label,
                        record: row,
                      ),
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
