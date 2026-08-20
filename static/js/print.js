// static/js/print.js
// One print path for browsers and native webviews.
//
// Android WebView / WKWebView / RN WebView have no window.print(), so a native
// shell exposes one of the bridges below. When a bridge is present window.print
// is rerouted through it, which means the existing onclick="window.print()"
// calls scattered across the templates keep working inside the app with no
// template changes.
//
// Payload handed to the shell (JSON):
//   {title, html, text, width}
//     html  - full document, for the system print / PDF path
//     text  - plain 32/48-column receipt body, ready for ESC/POS (thermal pages)
//     width - roll width in mm ("58"/"80"); empty on A4 pages
(function () {
    var nativePrint = window.print ? window.print.bind(window) : null;

    function payload() {
        var t = document.getElementById('receipt-text');
        return {
            title: document.title,
            html: '<!DOCTYPE html>' + document.documentElement.outerHTML,
            text: t ? t.textContent : '',
            width: document.body.getAttribute('data-roll-width') || ''
        };
    }

    // First bridge that answers wins.
    function send(data) {
        var a = window.HMSPrint || window.AndroidPrint || window.Android;
        if (a && typeof a.printReceipt === 'function') { a.printReceipt(JSON.stringify(data)); return true; }
        if (a && typeof a.print === 'function') { a.print(JSON.stringify(data)); return true; }
        if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage) {
            window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'print', payload: data }));
            return true;
        }
        if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.hmsPrint) {
            window.webkit.messageHandlers.hmsPrint.postMessage(data);
            return true;
        }
        if (window.flutter_inappwebview && window.flutter_inappwebview.callHandler) {
            window.flutter_inappwebview.callHandler('hmsPrint', data);
            return true;
        }
        return false;
    }

    function hmsPrint() {
        if (send(payload())) return;
        if (nativePrint) nativePrint();
        // ponytail: no "printing is unavailable" UI. A plain browser always has
        // window.print(), so this only fires in a webview whose shell forgot to
        // register a bridge - a shell bug, not a user situation.
    }

    window.hmsPrint = hmsPrint;

    // Reroute window.print only when a shell is actually listening.
    if (window.HMSPrint || window.AndroidPrint || window.Android ||
        window.ReactNativeWebView ||
        (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.hmsPrint) ||
        window.flutter_inappwebview) {
        window.print = hmsPrint;
    }

    if (document.body && document.body.getAttribute('data-auto-print') === '1') {
        window.addEventListener('load', function () { setTimeout(hmsPrint, 150); });
    }

    // Print a receipt without leaving the page: a hidden iframe loads it and
    // its own data-auto-print fires. A new tab would arrive without a session
    // inside the Flutter web shell, where the browser keeps our cookie in the
    // shell origin's partition and the receipt lands on the login page.
    function hmsPrintUrl(url) {
        var old = document.getElementById('hms-print-frame');
        if (old) old.parentNode.removeChild(old);
        var f = document.createElement('iframe');
        f.id = 'hms-print-frame';
        f.style.cssText = 'position:fixed;left:-9999px;width:1px;height:1px;border:0';
        f.src = url;
        document.body.appendChild(f);
    }

    window.hmsPrintUrl = hmsPrintUrl;

    // One delegated handler instead of an onclick in every receipt template.
    document.addEventListener('click', function (e) {
        var a = e.target && e.target.closest && e.target.closest('a[href]');
        if (!a || a.host !== location.host) return;
        if (/[?&]format=thermal/.test(a.href) && /[?&]auto=1/.test(a.href)) {
            e.preventDefault();
            hmsPrintUrl(a.href);
        } else if (a.target === '_blank' && window.top !== window.self &&
                   !/^\/(media|static)\//.test(a.pathname)) {
            // Same reason: in the shell a new tab has no session, so keep our
            // own pages (receipts, prints) inside this frame. Files under
            // /media/ and /static/ need no session, so let them have the tab.
            e.preventDefault();
            location.href = a.href;
        }
    });
})();
