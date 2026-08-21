"""JSON serialisation for values embedded in inline <script> blocks."""

import json


def json_for_template(obj, **kwargs):
    r"""json.dumps() with the characters that can break out of <script> escaped.

    json.dumps() leaves "</script>" untouched, so any user-supplied string that
    reaches a ``{{ value|safe }}`` inside an inline <script> block closes the
    tag and executes attacker HTML (stored XSS). Escaping <, > and & as \uXXXX
    keeps the result valid JSON -- JSON.parse and JS literals both accept the
    escapes -- while making that impossible.
    """
    return (
        json.dumps(obj, **kwargs)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _selfcheck():
    payload = "</script><script>alert(1)</script>"
    out = json_for_template([payload])
    assert "<" not in out and ">" not in out, out
    assert json.loads(out) == [payload], out
    assert json.loads(json_for_template({"a": "<b>&"})) == {"a": "<b>&"}
    print("json_for_template ok")


if __name__ == "__main__":
    _selfcheck()
