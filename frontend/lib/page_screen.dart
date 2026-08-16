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
  const PageScreen({super.key, required this.title, required this.path});

  final String title;
  final String path;

  @override
  State<PageScreen> createState() => _PageScreenState();
}

class _PageScreenState extends State<PageScreen> {
  late final WebViewController _controller;
  int _progress = 0;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (p) => setState(() => _progress = p),
          onPageFinished: (_) => setState(() => _progress = 100),
        ),
      )
      ..loadRequest(Uri.parse('$baseUrl${widget.path}'));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _controller.reload,
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
