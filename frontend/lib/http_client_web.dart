import 'package:http/browser_client.dart';
import 'package:http/http.dart' as http;

/// Web: send and store cookies. The browser will not keep Django's `sessionid`
/// from a cross-origin login — nor send it back — unless requests run with
/// credentials, and the iframe'd server-rendered pages need that session.
///
/// Requires the server to name this origin in CORS_ALLOWED_ORIGINS; a wildcard
/// `Access-Control-Allow-Origin` is rejected for credentialed requests.
http.Client createClient() => BrowserClient()..withCredentials = true;
