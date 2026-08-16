import 'package:flutter/material.dart';

import '../api.dart';
import '../paged_list.dart';
import 'admissions.dart';

/// The ward board: occupancy per ward, tap through to the bed map.
class WardBoardScreen extends StatefulWidget {
  const WardBoardScreen({super.key});

  @override
  State<WardBoardScreen> createState() => _WardBoardScreenState();
}

class _WardBoardScreenState extends State<WardBoardScreen> {
  int _reloadToken = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Wards')),
      body: PagedList(
        key: ValueKey(_reloadToken),
        path: '/inpatient/api/wards/',
        query: const {},
        emptyMessage: 'No wards',
        itemBuilder: (context, row) {
          final free = row['available_beds'] as int? ?? 0;
          return ListTile(
            leading: CircleAvatar(
              backgroundColor: free == 0
                  ? Theme.of(context).colorScheme.errorContainer
                  : Theme.of(context).colorScheme.secondaryContainer,
              child: Text('$free'),
            ),
            title: Text('${row['name']}'),
            subtitle: Text(
              '${row['ward_type_display']} · floor ${row['floor']}\n'
              '${row['occupied_beds']} occupied of ${row['total_beds']} · '
              '₦${row['charge_per_day']}/day',
            ),
            isThreeLine: true,
            onTap: () async {
              await Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => BedMapScreen(ward: row)),
              );
              setState(() => _reloadToken++);
            },
          );
        },
      ),
    );
  }
}

/// The beds in one ward, with who is in them.
class BedMapScreen extends StatefulWidget {
  const BedMapScreen({super.key, required this.ward});

  final Map<String, dynamic> ward;

  @override
  State<BedMapScreen> createState() => _BedMapScreenState();
}

class _BedMapScreenState extends State<BedMapScreen> {
  int _reloadToken = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('${widget.ward['name']}')),
      body: PagedList(
        key: ValueKey(_reloadToken),
        path: '/inpatient/api/beds/',
        query: {'ward': '${widget.ward['id']}'},
        emptyMessage: 'No beds in this ward',
        itemBuilder: (context, row) {
          final occupied = row['is_occupied'] == true;
          return ListTile(
            leading: Icon(
              occupied ? Icons.bed : Icons.bed_outlined,
              color: occupied ? Theme.of(context).colorScheme.primary : null,
            ),
            title: Text('Bed ${row['bed_number']}'),
            subtitle: Text(
              occupied
                  ? '${row['patient_name']}'
                  : row['is_active'] == true
                      ? 'Free'
                      : 'Out of service',
            ),
            onTap: occupied
                ? () async {
                    await _openAdmissionInBed(context, row['id'] as int);
                    setState(() => _reloadToken++);
                  }
                : null,
          );
        },
      ),
    );
  }
}

/// The bed map knows the bed, not the admission — ask the server which one.
Future<void> _openAdmissionInBed(BuildContext context, int bedId) async {
  try {
    final data = await Api.get('/inpatient/api/admissions/', {'status': 'all'});
    final match = (data['results'] as List)
        .cast<Map<String, dynamic>>()
        .where((a) => a['bed'] == bedId && a['is_active'] == true);
    if (match.isEmpty || !context.mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AdmissionScreen(admissionId: match.first['id'] as int),
      ),
    );
  } on ApiException catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    }
  }
}
