import 'package:http/http.dart' as http;

/// Mobile and desktop: the plain client, with the token in the header doing all
/// the authenticating.
http.Client createClient() => http.Client();
