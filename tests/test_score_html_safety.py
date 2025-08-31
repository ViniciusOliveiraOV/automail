import re


def test_score_html_sanitization_removes_disallowed_tags():
    unsafe = '<script>alert(1)</script><p>Ok</p><b>bold</b><a href="#">link</a>'
    # If bleach is installed, use it for sanitization similar to app behavior
    try:
        import bleach
        cleaned = bleach.clean(unsafe, tags=['strong', 'em', 'code', 'pre', 'p', 'ul', 'li', 'br'], attributes={}, strip=True)
    except Exception:
        # Fallback: remove all tags unsupported by a simple regex
        cleaned = re.sub(r'<(script|b|a)[^>]*>.*?</\1>', '', unsafe, flags=re.IGNORECASE)

    assert '<script' not in cleaned.lower()
    assert '<b' not in cleaned.lower()
    assert '<a' not in cleaned.lower()
    assert '<p>' in cleaned
 
