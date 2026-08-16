import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

import 'config.dart';

/// One screen for any Django page. The server already renders every template
/// (Bootstrap 5, responsive) including its modals, so a single screen covers
/// all ~970 routes instead of one hand-written widget per template.
///
/// ponytail: WebView, not native widgets. Native screens would need a JSON
/// endpoint per template and none exist yet -- build those per module first,
/// then swap individual routes over to native screens as the APIs land.
class PageScreen extends StatefulWidget {
  const PageScreen({
    super.key,
    required this.title,
    required this.path,
    this.actions = const [],
    this.bare = false,
    this.onSessionEnded,
  });

  final String title;
  final String path;

  /// Extra app-bar buttons, ahead of the reload button.
  final List<Widget> actions;

  /// Drop the Flutter app bar and show the page alone. The Django templates
  /// carry their own header and navigation, so a second bar above them is
  /// wasted height on a phone.
  final bool bare;

  /// Called when the WebView lands on the sign-in page, which means Django
  /// ended the session (the topbar's logout) without the app knowing.
  final VoidCallback? onSessionEnded;

  @override
  State<PageScreen> createState() => _PageScreenState();
}

class _PageScreenState extends State<PageScreen> {
  late final WebViewController _controller;
  int _progress = 0;

  Uri get _uri => Uri.parse('$baseUrl${widget.path}');

  @override
  void initState() {
    super.initState();
    _controller = WebViewController();
    // The web implementation is a bare iframe: JavaScript is the browser's
    // business and there is no navigation callback, so both calls throw there.
    // Without progress events, show the page as loaded straight away.
    if (kIsWeb) {
      _progress = 100;
    } else {
      _controller
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setNavigationDelegate(
          NavigationDelegate(
            onProgress: (p) => setState(() => _progress = p),
            onPageFinished: (url) {
              setState(() => _progress = 100);
              if (Uri.parse(url).path.startsWith('/accounts/login')) {
                widget.onSessionEnded?.call();
              }
            },
          ),
        );
    }
    _controller.loadRequest(_uri);
  }

  // `reload` is unimplemented on web; re-pointing the iframe does the same job.
  void _reload() => kIsWeb ? _controller.loadRequest(_uri) : _controller.reload();

  @override
  Widget build(BuildContext context) {
    if (widget.bare) {
      return Scaffold(
        body: SafeArea(
          child: Column(
            children: [
              if (_progress < 100)
                LinearProgressIndicator(value: _progress / 100),
              Expanded(child: WebViewWidget(controller: _controller)),
            ],
          ),
        ),
      );
    }
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title, overflow: TextOverflow.ellipsis),
        actions: [
          ...widget.actions,
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _reload,
          ),
        ],
        bottom: _progress < 100
            ? PreferredSize(
                preferredSize: const Size.fromHeight(2),
                child: LinearProgressIndicator(value: _progress / 100),
              )
            : null,
      ),
      body: WebViewWidget(controller: _controller),
    );
  }
}
