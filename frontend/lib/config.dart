import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb, TargetPlatform;

/// Base URL of the Django server.
///
/// Override at build time:
///   flutter run --dart-define=HMS_BASE_URL=http://192.168.1.10:8000
const _envBaseUrl = String.fromEnvironment('HMS_BASE_URL');

/// Only the Android emulator needs 10.0.2.2 to reach the host's localhost;
/// every other target (web, desktop, iOS simulator) talks to localhost directly.
/// A physical device needs the LAN IP via --dart-define.
final baseUrl = _envBaseUrl.isNotEmpty
    ? _envBaseUrl
    : (!kIsWeb && defaultTargetPlatform == TargetPlatform.android
        ? 'http://10.0.2.2:8000'
        : 'http://localhost:8000');

const loginPath = '/accounts/login/';
const homePath = '/dashboard/';
