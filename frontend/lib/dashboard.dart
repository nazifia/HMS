import 'package:flutter/material.dart';

import 'api.dart';
import 'billing/billing.dart';
import 'consultations/consultations.dart';
import 'inpatient/wards.dart';
import 'laboratory/laboratory.dart';
import 'main.dart';
import 'pharmacy/inventory.dart';

/// The landing screen: what needs attention now, straight into the screen that
/// deals with it. The server decides which tiles a user gets, so anything shown
/// here is something they are allowed to open.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key, required this.onSignOut});

  final Future<void> Function() onSignOut;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

/// Tile key from `/api/dashboard/` → the screen that acts on it.
final _screens = <String, Widget Function()>{
  'clinic_queue': ClinicScreen.new,
  'unpaid_invoices': InvoiceListScreen.new,
  'lab_verification': TestRequestListScreen.new,
  'low_stock': InventoryScreen.new,
  'free_beds': WardBoardScreen.new,
};

const _icons = <String, IconData>{
  'clinic_queue': Icons.local_hospital,
  'unpaid_invoices': Icons.request_quote,
  'lab_verification': Icons.science,
  'low_stock': Icons.inventory_2,
  'free_beds': Icons.meeting_room,
};

class _DashboardScreenState extends State<DashboardScreen> {
  List<dynamic>? _tiles;
  String? _error;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    try {
      final data = await Api.get('/api/dashboard/');
      if (!mounted) return;
      setState(() {
        _tiles = data['tiles'] as List<dynamic>;
        _error = null;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('HMS'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
            onPressed: widget.onSignOut,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: ListView(
          children: [
            if (_error != null)
              ListTile(
                leading: const Icon(Icons.error_outline),
                title: Text(_error!),
              ),
            if (_tiles == null && _error == null)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              ),
            for (final tile in _tiles ?? const [])
              _TileCard(
                tile: tile as Map<String, dynamic>,
                onTap: _screens[tile['key']],
              ),
            const Divider(height: 1),
            ListTile(
              leading: const Icon(Icons.apps),
              title: const Text('All modules'),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ModuleListScreen(onSignOut: widget.onSignOut),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TileCard extends StatelessWidget {
  const _TileCard({required this.tile, this.onTap});

  final Map<String, dynamic> tile;
  final Widget Function()? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      child: ListTile(
        leading: Icon(_icons[tile['key']] ?? Icons.insights),
        title: Text('${tile['label']}'),
        subtitle: Text('${tile['note']}'),
        trailing: Text(
          '${tile['count']}',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        onTap: onTap == null
            ? null
            : () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => onTap!()),
                ),
      ),
    );
  }
}
