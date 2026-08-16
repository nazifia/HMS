import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

import 'api.dart';
import 'config.dart';

/// Hand the Django session cookie to the WebView screens.
///
/// No-op on web, where there is no separate WebView cookie store: the iframe
/// shares the browser's jar, which the credentialed login already filled.
Future<void> applySessionCookie(String? sessionId) async {
  if (kIsWeb || sessionId == null) return;
  await WebViewCookieManager().setCookie(
    WebViewCookie(
      name: 'sessionid',
      value: sessionId,
      domain: Uri.parse(baseUrl).host,
    ),
  );
}

/// Drop the WebView's copy of the session, so the server-rendered screens are
/// signed out too rather than running on a session the native side abandoned.
/// On web that cookie is the browser's and HttpOnly, so `Api.signOut` ends the
/// session server-side instead.
Future<void> clearSessionCookie() =>
    kIsWeb ? Future.value() : WebViewCookieManager().clearCookies();

/// Phone + password against `/api/accounts/login/`.
///
/// That endpoint returns a token *and* opens a Django session, so we keep the
/// token for the native screens and push the session cookie into the WebView —
/// one sign-in serves both.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.onSignedIn, this.notice});

  final VoidCallback onSignedIn;

  /// Why the user is back here — "Session expired", typically.
  final String? notice;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phone = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final response = await Api.postJson('/api/accounts/login/', {
        'phone_number': _phone.text.trim(),
        'password': _password.text,
      });
      final body = jsonDecode(utf8.decode(response.bodyBytes));
      if (response.statusCode != 200) {
        setState(() => _error = body['error']?.toString() ?? 'Sign in failed');
        return;
      }
      final sessionId = sessionIdFrom(response.headers['set-cookie']);
      await Api.save(body['token'] as String, sessionId);
      await applySessionCookie(sessionId);
      widget.onSignedIn();
    } catch (e) {
      setState(() => _error = 'Cannot reach $baseUrl');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('HMS', style: Theme.of(context).textTheme.headlineMedium),
              if (widget.notice != null) ...[
                const SizedBox(height: 12),
                Text(widget.notice!, textAlign: TextAlign.center),
              ],
              const SizedBox(height: 24),
              TextField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(
                  labelText: 'Phone number',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _password,
                obscureText: true,
                onSubmitted: (_) => _busy ? null : _submit(),
                decoration: const InputDecoration(
                  labelText: 'Password',
                  border: OutlineInputBorder(),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _busy ? null : _submit,
                  child: _busy
                      ? const SizedBox(
                          height: 18,
                          width: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Sign in'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
