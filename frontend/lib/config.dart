/// Base URL of the Django server.
///
/// Override at build time:
///   flutter run --dart-define=HMS_BASE_URL=http://192.168.1.10:8000
///
/// Default is the Android emulator's alias for the host machine's localhost.
const baseUrl = String.fromEnvironment(
  'HMS_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);

const loginPath = '/accounts/login/';
const homePath = '/dashboard/';
