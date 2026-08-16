import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

import 'api.dart';
import 'config.dart';

/// Hand the Django session cookie to the WebView screens.
Future<void> applySessionCookie(String? sessionId) async {
  if (sessionId == null) return;
  await WebViewCookieManager().setCookie(
    WebViewCookie(
      name: 'sessionid',
      value: sessionId,
      domain: Uri.parse(baseUrl).host,
    ),
  );
}

/// Phone + password against `/api/accounts/login/`.
///
/// That endpoint returns a token *and* opens a Django session, so we keep the
/// token for the native screens and push the session cookie into the WebView —
/// one sign-in serves both.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.onSignedIn});

  final VoidCallback onSignedIn;

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
