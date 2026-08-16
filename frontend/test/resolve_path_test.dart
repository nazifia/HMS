import 'package:flutter_test/flutter_test.dart';
import 'package:hms_frontend/api.dart';
import 'package:hms_frontend/main.dart';

void main() {
  test('sessionIdFrom picks the session cookie out of Set-Cookie', () {
    expect(
      sessionIdFrom(
        'sessionid=abc123; expires=Fri, 15 Aug 2026 07:00:00 GMT; Path=/',
      ),
      'abc123',
    );
    // Dart joins repeated Set-Cookie headers with commas.
    expect(
      sessionIdFrom('csrftoken=zzz; Path=/, sessionid=xyz789; HttpOnly'),
      'xyz789',
    );
    expect(sessionIdFrom('csrftoken=zzz; Path=/'), isNull);
    expect(sessionIdFrom(null), isNull);
  });

  test('resolvePath fills params and escapes values', () {
    expect(resolvePath('/patients/<pk>/', {'pk': '42'}), '/patients/42/');
    expect(
      resolvePath('/pharmacy/<a>/x/<b>/', {'a': '1', 'b': '2'}),
      '/pharmacy/1/x/2/',
    );
    expect(resolvePath('/s/<q>/', {'q': 'a b/c'}), '/s/a%20b%2Fc/');
    expect(resolvePath('/billing/list/', {}), '/billing/list/');
  });
}
