import 'package:flutter/material.dart';

import 'api.dart';
import 'login.dart';
import 'appointments/appointments.dart';
import 'billing/billing.dart';
import 'consultations/consultations.dart';
import 'inpatient/admissions.dart';
import 'inpatient/wards.dart';
import 'laboratory/laboratory.dart';
import 'nhia/authorization.dart';
import 'radiology/radiology.dart';
import 'specialty/specialty.dart';
import 'theatre/theatre.dart';
import 'page_screen.dart';
import 'patients/patients.dart';
import 'pharmacy/carts.dart';
import 'pharmacy/dispensary_admin.dart';
import 'pharmacy/dispensing_log.dart';
import 'pharmacy/expenses.dart';
import 'pharmacy/inventory.dart';
import 'pharmacy/packs.dart';
import 'pharmacy/medications.dart';
import 'pharmacy/prescriptions.dart';
import 'pharmacy/purchases.dart';
import 'pharmacy/transfers.dart';
import 'routes.dart';

void main() => runApp(const HmsApp());

/// Substitute `<param>` placeholders in a route path with user-supplied values.
String resolvePath(String path, Map<String, String> values) {
  return path.replaceAllMapped(RegExp(r'<([^>]+)>'), (m) {
    final value = values[m[1]] ?? '';
    return Uri.encodeComponent(value);
  });
}

class HmsApp extends StatefulWidget {
  const HmsApp({super.key});

  @override
  State<HmsApp> createState() => _HmsAppState();
}

class _HmsAppState extends State<HmsApp> {
  final _navigator = GlobalKey<NavigatorState>();
  bool _signedIn = false;
  bool _restoring = true;
  String? _notice;

  @override
  void initState() {
    super.initState();
    Api.onUnauthorized = () => _bounceToLogin();
    _restore();
  }

  @override
  void dispose() {
    Api.onUnauthorized = null;
    super.dispose();
  }

  /// The token expired or was revoked: drop it, close whatever screen raised
  /// the 401 along with anything stacked under it, and ask for a sign-in.
  Future<void> _bounceToLogin() async {
    if (!_signedIn) return;
    await Api.signOut();
    await clearSessionCookie();
    _navigator.currentState?.popUntil((route) => route.isFirst);
    if (mounted) {
      setState(() {
        _signedIn = false;
        _notice = 'Session expired. Sign in again.';
      });
    }
  }

  Future<void> _signOut() async {
    await Api.signOut();
    await clearSessionCookie();
    _navigator.currentState?.popUntil((route) => route.isFirst);
    if (mounted) setState(() => _signedIn = false);
  }

  Future<void> _restore() async {
    final sessionId = await Api.restore();
    await applySessionCookie(sessionId);
    if (mounted) {
      setState(() {
        _signedIn = Api.token != null;
        _restoring = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'HMS',
      debugShowCheckedModeBanner: false,
      navigatorKey: _navigator,
      theme: ThemeData(colorSchemeSeed: Colors.teal, useMaterial3: true),
      home: _restoring
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : _signedIn
              // The Django dashboard is the home screen: it carries the same
              // figures as the native tiles plus its own sidebar, and stays in
              // step with the web app for free.
              // ponytail: `lib/dashboard.dart` is left in place unrouted --
              // put `DashboardScreen(onSignOut: _signOut)` back here to return.
              // ponytail: no app bar and no "All modules" button -- the page's
              // own header and sidebar reach everything, and the native screens
              // stay reachable through ModuleListScreen if one is routed back.
              ? PageScreen(
                  title: 'HMS',
                  path: '/dashboard/',
                  bare: true,
                  onSessionEnded: _signOut,
                )
              : LoginScreen(
                  notice: _notice,
                  onSignedIn: () => setState(() {
                    _signedIn = true;
                    _notice = null;
                  }),
                ),
    );
  }
}

/// Modules, derived from the first path segment of every generated route.
class ModuleListScreen extends StatelessWidget {
  const ModuleListScreen({super.key, required this.onSignOut});

  final Future<void> Function() onSignOut;

  @override
  Widget build(BuildContext context) {
    final counts = <String, int>{};
    for (final r in hmsRoutes) {
      counts[r.module] = (counts[r.module] ?? 0) + 1;
    }
    final modules = counts.keys.toList()..sort();

    return Scaffold(
      appBar: AppBar(
        title: const Text('HMS'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () => showSearch(
              context: context,
              delegate: RouteSearchDelegate(),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
            onPressed: onSignOut,
          ),
        ],
      ),
      body: ListView.separated(
        itemCount: _nativeScreens.length + modules.length + 1,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, i) {
          if (i == 0) {
            return ListTile(
              leading: const Icon(Icons.dashboard),
              title: const Text('Dashboard'),
              onTap: () => _open(
                context,
                const HmsRoute('dashboard', '/dashboard/', 'dashboard', []),
              ),
            );
          }
          if (i <= _nativeScreens.length) {
            final entry = _nativeScreens[i - 1];
            return ListTile(
              leading: Icon(entry.icon),
              title: Text(entry.title),
              subtitle: const Text('native'),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => entry.build()),
              ),
            );
          }
          final module = modules[i - _nativeScreens.length - 1];
          return ListTile(
            leading: const Icon(Icons.folder_outlined),
            title: Text(module.replaceAll('-', ' ')),
            trailing: Text('${counts[module]}'),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => ModuleScreensScreen(module: module),
              ),
            ),
          );
        },
      ),
    );
  }
}

/// Screens built on `/pharmacy/api/` rather than rendered by Django.
class _NativeScreen {
  const _NativeScreen(this.title, this.icon, this.build);

  final String title;
  final IconData icon;
  final Widget Function() build;
}

const _nativeScreens = <_NativeScreen>[
  _NativeScreen('Patients', Icons.people, PatientListScreen.new),
  _NativeScreen('Appointments', Icons.event, AppointmentListScreen.new),
  _NativeScreen('Clinic', Icons.local_hospital, ClinicScreen.new),
  _NativeScreen('Invoices', Icons.request_quote, InvoiceListScreen.new),
  _NativeScreen('Lab requests', Icons.science, TestRequestListScreen.new),
  _NativeScreen('Radiology', Icons.monitor_heart, RadiologyOrderListScreen.new),
  _NativeScreen('Wards', Icons.meeting_room, WardBoardScreen.new),
  _NativeScreen('Admissions', Icons.airline_seat_flat, AdmissionListScreen.new),
  _NativeScreen('Theatre list', Icons.airline_seat_recline_extra, TheatreListScreen.new),
  _NativeScreen('Specialty clinics', Icons.local_hospital_outlined, SpecialtyModulesScreen.new),
  _NativeScreen('NHIA authorization', Icons.verified_user, AuthorizationScreen.new),
  _NativeScreen('Prescriptions', Icons.receipt_long, PrescriptionListScreen.new),
  _NativeScreen('Dispensing carts', Icons.shopping_cart, CartListScreen.new),
  _NativeScreen('Medications & stock', Icons.medication, MedicationListScreen.new),
  _NativeScreen('Dispensary inventory', Icons.inventory_2, InventoryScreen.new),
  _NativeScreen('Stock transfers', Icons.swap_horiz, TransfersScreen.new),
  _NativeScreen('Dispensing log', Icons.history, DispensingLogScreen.new),
  _NativeScreen('Purchase orders', Icons.local_shipping, PurchaseListScreen.new),
  _NativeScreen('Medical packs', Icons.medical_services, PacksScreen.new),
  _NativeScreen('Expenses', Icons.receipt, ExpensesScreen.new),
  _NativeScreen('Dispensaries', Icons.storefront, DispensaryAdminScreen.new),
];

/// Every screen inside one module.
class ModuleScreensScreen extends StatelessWidget {
  const ModuleScreensScreen({super.key, required this.module});

  final String module;

  @override
  Widget build(BuildContext context) {
    final routes = hmsRoutes.where((r) => r.module == module).toList();
    return Scaffold(
      appBar: AppBar(title: Text(module.replaceAll('-', ' '))),
      body: ListView.separated(
        itemCount: routes.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, i) => _RouteTile(route: routes[i]),
      ),
    );
  }
}

class RouteSearchDelegate extends SearchDelegate<void> {
  @override
  List<Widget> buildActions(BuildContext context) => [
        IconButton(
          icon: const Icon(Icons.clear),
          onPressed: () => query = '',
        ),
      ];

  @override
  Widget buildLeading(BuildContext context) => IconButton(
        icon: const Icon(Icons.arrow_back),
        onPressed: () => close(context, null),
      );

  @override
  Widget buildResults(BuildContext context) => buildSuggestions(context);

  @override
  Widget buildSuggestions(BuildContext context) {
    final q = query.toLowerCase().trim();
    if (q.isEmpty) return const SizedBox.shrink();
    final hits = hmsRoutes
        .where((r) =>
            r.name.toLowerCase().contains(q) || r.path.toLowerCase().contains(q))
        .take(100)
        .toList();
    return ListView.separated(
      itemCount: hits.length,
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemBuilder: (context, i) => _RouteTile(route: hits[i]),
    );
  }
}

class _RouteTile extends StatelessWidget {
  const _RouteTile({required this.route});

  final HmsRoute route;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      title: Text(route.label),
      subtitle: Text(route.path, style: Theme.of(context).textTheme.bodySmall),
      trailing: route.params.isEmpty ? null : const Icon(Icons.edit_outlined),
      onTap: () => _open(context, route),
    );
  }
}

Future<void> _open(BuildContext context, HmsRoute route) async {
  var path = route.path;
  if (route.params.isNotEmpty) {
    final values = await _askParams(context, route);
    if (values == null || !context.mounted) return;
    path = resolvePath(path, values);
  }
  if (!context.mounted) return;
  Navigator.of(context).push(
    MaterialPageRoute(
      builder: (_) => PageScreen(title: route.label, path: path),
    ),
  );
}

/// Routes like `/patients/<patient_id>/` need an id before they can be opened.
Future<Map<String, String>?> _askParams(
  BuildContext context,
  HmsRoute route,
) {
  final controllers = {
    for (final p in route.params) p: TextEditingController(),
  };
  return showDialog<Map<String, String>>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(route.label),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final p in route.params)
            TextField(
              controller: controllers[p],
              decoration: InputDecoration(labelText: p),
            ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(
            context,
            controllers.map((k, v) => MapEntry(k, v.text.trim())),
          ),
          child: const Text('Open'),
        ),
      ],
    ),
  );
}
