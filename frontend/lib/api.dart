import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'config.dart';
import 'http_client_io.dart'
    if (dart.library.js_interop) 'http_client_web.dart';

class ApiException implements Exception {
  ApiException(this.message, [this.body]);

  final String message;

  /// Decoded response body, when there was one — a 409 on cart creation
  /// carries the cart that already exists.
  final dynamic body;

  @override
  String toString() => message;
}

/// Talks to the Django REST endpoints under `/pharmacy/api/`.
///
/// The token is a credential, so it goes to the platform keystore/keychain
/// rather than plain preferences.
class Api {
  static const _store = FlutterSecureStorage();
  static const _tokenKey = 'hms_token';
  static const _sessionKey = 'hms_sessionid';

  /// One client for the whole app: on web it is the credentialed browser client
  /// that carries Django's session cookie, elsewhere the plain one.
  static final _client = createClient();

  static String? token;

  /// Called when the server rejects our token (expired, revoked, or the user
  /// was deactivated). Set once by the app so every screen bounces to login
  /// instead of each showing its own "session expired" error.
  static void Function()? onUnauthorized;

  /// Restores a saved sign-in. Returns the Django session cookie, if any, so
  /// the caller can hand it back to the WebView.
  static Future<String?> restore() async {
    token = await _store.read(key: _tokenKey);
    return token == null ? null : await _store.read(key: _sessionKey);
  }

  static Future<void> save(String newToken, String? sessionId) async {
    token = newToken;
    await _store.write(key: _tokenKey, value: newToken);
    await _store.write(key: _sessionKey, value: sessionId);
  }

  static Future<void> signOut() async {
    token = null;
    await _store.delete(key: _tokenKey);
    await _store.delete(key: _sessionKey);
    if (kIsWeb) {
      // The session cookie is HttpOnly and cross-origin, so the page cannot
      // drop it — ask the server to end the session instead. Best effort: a
      // failure here still leaves the client signed out.
      try {
        await _client.get(Uri.parse('$baseUrl/accounts/logout/'));
      } catch (_) {}
    }
  }

  static Map<String, String> get _headers => {
        'Accept': 'application/json',
        if (token != null) 'Authorization': 'Token $token',
      };

  static Future<dynamic> get(String path, [Map<String, String>? query]) async {
    final uri = Uri.parse('$baseUrl$path').replace(
      queryParameters: {...?query}..removeWhere((_, v) => v.isEmpty),
    );
    return _decode(await _client.get(uri, headers: _headers));
  }

  /// Follows a DRF `next` link, which already carries the query string.
  static Future<dynamic> getUrl(String url) async {
    return _decode(await _client.get(Uri.parse(url), headers: _headers));
  }

  /// Raw POST, used by the login screen which needs the Set-Cookie header.
  static Future<http.Response> postJson(
    String path,
    Map<String, dynamic> body,
  ) {
    return _client.post(
      Uri.parse('$baseUrl$path'),
      headers: {..._headers, 'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
  }

  static Future<dynamic> post(String path, [Map<String, dynamic>? body]) async {
    return _decode(await postJson(path, body ?? {}));
  }

  /// POST a form with files attached (radiology studies, result files, photos).
  /// `fields` are sent as plain form values, so send only what was filled in.
  static Future<dynamic> postMultipart(
    String path,
    Map<String, String> fields, {
    Map<String, String> files = const {},
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl$path'))
      ..headers.addAll(_headers)
      ..fields.addAll(fields);
    for (final entry in files.entries) {
      request.files
          .add(await http.MultipartFile.fromPath(entry.key, entry.value));
    }
    return _decode(await http.Response.fromStream(await _client.send(request)));
  }

  static Future<dynamic> patch(String path, Map<String, dynamic> body) async {
    return _decode(await _client.patch(
      Uri.parse('$baseUrl$path'),
      headers: {..._headers, 'Content-Type': 'application/json'},
      body: jsonEncode(body),
    ));
  }

  static Future<dynamic> delete(String path) async {
    return _decode(
        await _client.delete(Uri.parse('$baseUrl$path'), headers: _headers));
  }

  static dynamic _decode(http.Response response) {
    // The server redirects unauthorised pharmacy requests to an HTML page (e.g.
    // a pharmacist with no dispensary assigned); http follows the redirect, so
    // a 200 alone does not mean we got JSON.
    final isJson = (response.headers['content-type'] ?? '').contains('json');
    if (!isJson) {
      if (response.statusCode == 204) return null;
      throw ApiException(
        'Not permitted: the server returned a page, not data. '
        'Check your pharmacy role and dispensary assignment.',
      );
    }

    final body = jsonDecode(utf8.decode(response.bodyBytes));
    if (response.statusCode < 400) return body;
    if (response.statusCode == 401) {
      // Both gates answer 401: DRF for an expired token, the access-control
      // middleware for a request that arrived without one.
      onUnauthorized?.call();
      throw ApiException('Session expired. Sign in again.');
    }
    // `detail` carries the actual reason ("You have not been assigned to any
    // dispensary yet"); `error` is the category.
    final message = body is Map ? body['detail'] ?? body['error'] : null;
    throw ApiException(
      message?.toString() ?? 'Server error ${response.statusCode}',
      body,
    );
  }
}

/// DRF sends decimals as strings; this only needs "is there anything there".
extension Decimalish on Object? {
  bool get isPositive => (double.tryParse('${this ?? 0}') ?? 0) > 0;
}

/// Pull `sessionid` out of a Set-Cookie header so the WebView screens share the
/// session the token login just created. Dart joins repeated Set-Cookie headers
/// with commas, and `expires=` values contain commas too, so parse by name.
///
/// Always null on web: browsers hide Set-Cookie from page code. There the
/// credentialed client has already handed the cookie to the browser's own jar,
/// which is what the iframe reads, so nothing is lost.
String? sessionIdFrom(String? setCookieHeader) {
  if (setCookieHeader == null) return null;
  final match = RegExp(r'sessionid=([^;,\s]+)').firstMatch(setCookieHeader);
  return match?.group(1);
}
