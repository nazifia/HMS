import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';

/// Create dispensaries and see who is assigned to each.
class DispensaryAdminScreen extends StatefulWidget {
  const DispensaryAdminScreen({super.key});

  @override
  State<DispensaryAdminScreen> createState() => _DispensaryAdminScreenState();
}

class _DispensaryAdminScreenState extends State<DispensaryAdminScreen> {
  int _reloadToken = 0;

  Future<void> _newDispensary() async {
    final name = TextEditingController();
    final location = TextEditingController();
    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New dispensary'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              autofocus: true,
              decoration: const InputDecoration(labelText: 'Name'),
            ),
            TextField(
              controller: location,
              decoration: const InputDecoration(labelText: 'Location'),
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
            child: const Text('Create'),
          ),
        ],
      ),
    );
    if (saved != true || name.text.trim().isEmpty) return;

    try {
      await Api.post('/pharmacy/api/manage-dispensaries/', {
        'name': name.text.trim(),
        'location': location.text.trim(),
      });
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
    return Scaffold(
      appBar: AppBar(title: const Text('Dispensaries')),
      floatingActionButton: FloatingActionButton(
        onPressed: _newDispensary,
        child: const Icon(Icons.add),
      ),
      body: PagedList(
        key: ValueKey(_reloadToken),
        path: '/pharmacy/api/manage-dispensaries/',
        query: const {},
        emptyMessage: 'No dispensaries',
        itemBuilder: (context, row) => ListTile(
          title: Text('${row['name']}'),
          subtitle: Text(
            '${row['location'] ?? 'no location'}'
            '${row['manager_name']?.isEmpty ?? true ? '' : ' · managed by ${row['manager_name']}'}',
          ),
          trailing: Text('${row['pharmacist_count']} staff'),
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => DispensaryStaffScreen(dispensary: row),
            ),
          ),
        ),
      ),
    );
  }
}

class DispensaryStaffScreen extends StatefulWidget {
  const DispensaryStaffScreen({super.key, required this.dispensary});

  final Map<String, dynamic> dispensary;

  @override
  State<DispensaryStaffScreen> createState() => _DispensaryStaffScreenState();
}

class _DispensaryStaffScreenState extends State<DispensaryStaffScreen> {
  List<Map<String, dynamic>>? _staff;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final rows = await Api.get(
        '/pharmacy/api/manage-dispensaries/${widget.dispensary['id']}/pharmacists/',
      ) as List;
      if (mounted) {
        setState(() {
          _staff = rows.cast<Map<String, dynamic>>();
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final staff = _staff;
    return Scaffold(
      appBar: AppBar(title: Text('${widget.dispensary['name']}')),
      body: _error != null
          ? Center(child: Text(_error!))
          : staff == null
              ? const Center(child: CircularProgressIndicator())
              : staff.isEmpty
                  ? const Center(child: Text('No pharmacists assigned'))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        itemCount: staff.length,
                        separatorBuilder: (_, __) => const Divider(height: 1),
                        itemBuilder: (context, i) => ListTile(
                          leading: const Icon(Icons.person_outline),
                          title: Text('${staff[i]['pharmacist_name']}'),
                          subtitle: Text(
                            'since ${staff[i]['start_date'].toString().split('T').first}',
                          ),
                        ),
                      ),
                    ),
    );
  }
}
