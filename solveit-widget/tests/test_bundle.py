"""Guards on the shipped frontend bundle.

anywidget (>=0.9) requires the ESM module to expose a DEFAULT export implementing
the widget lifecycle (`render`/`initialize`). A bare named `export function render`
is rejected at load time with "does not appear to be a valid anywidget". These
tests fail loudly if the bundle regresses to that shape.
"""

from solveit_widget.widget import _STATIC


def test_bundle_exists_and_nonempty():
    bundle = _STATIC / "index.js"
    assert bundle.exists(), "frontend bundle missing — run `cd frontend && npm run build`"
    assert bundle.stat().st_size > 0


def test_bundle_has_default_export():
    src = (_STATIC / "index.js").read_text()
    assert "as default" in src or "default:" in src, (
        "frontend bundle has no default export; anywidget will reject it"
    )
