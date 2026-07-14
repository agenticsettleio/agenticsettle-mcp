"""Regression guard for the .mcpb vendored-lib bootstrap (2026-07-14).

manifest.json sets PYTHONPATH=${__dirname}/lib for the packaged install,
which only appends that directory to sys.path *raw* — it does NOT process
.pth files inside it. On Windows, `mcp` unconditionally needs pywintypes/
win32api/win32con/win32job, which pywin32 only exposes via a .pth-based
redirect into a nested lib/win32/lib/ subdirectory. Without server.py's
site.addsitedir() bootstrap, the packaged server fails to import on any
machine without a separately-installed global pywin32 — this was caught by
testing the actual packaged .mcpb in true isolation (`python -S`, no global
site-packages), not by any plain smoke test, because a dev machine that
happens to have pywin32 installed globally silently masks the bug.

This suite doesn't vendor real pywin32 (too slow/heavy for CI) — it proves
the *general mechanism* server.py relies on (site.addsitedir() surfaces a
.pth-redirected submodule that a raw sys.path entry cannot) using a tiny
synthetic package, and separately asserts server.py still contains the
bootstrap so it can't be silently deleted by a future refactor.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path


def test_server_source_still_has_the_lib_bootstrap():
    src = (Path(__file__).resolve().parents[1] / "agenticsettle_verify_mcp" / "server.py").read_text(encoding="utf-8")
    assert "site.addsitedir(_LIB_DIR)" in src, (
        "server.py's .mcpb vendored-lib bootstrap was removed — this breaks "
        "the packaged Windows install for anyone without a separate global "
        "pywin32 (see the module-level comment above _LIB_DIR in server.py)."
    )
    assert src.index("site.addsitedir(_LIB_DIR)") < src.index("import httpx"), (
        "the bootstrap must run before any mcp-dependent import, or it's too late"
    )


def test_pth_redirected_submodule_unreachable_via_raw_syspath(tmp_path):
    """Without addsitedir, a .pth-redirected submodule is NOT importable —
    this is the exact failure mode the bootstrap fixes (proven against a
    tiny synthetic package, not real pywin32)."""
    _make_synthetic_pth_package(tmp_path)
    script = f"""
        import sys
        sys.path.insert(0, {str(tmp_path)!r})
        import synth_marker
    """
    result = subprocess.run(
        [sys.executable, "-S", "-c", textwrap.dedent(script)],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode != 0, "expected ModuleNotFoundError without addsitedir"
    assert "synth_marker" in result.stderr


def test_addsitedir_bootstrap_makes_the_pth_redirected_submodule_importable(tmp_path):
    """The exact fix: site.addsitedir() on the vendored dir processes the
    .pth file and makes the redirected submodule importable — same
    mechanism server.py's bootstrap applies to pywin32's win32/lib/ redirect."""
    _make_synthetic_pth_package(tmp_path)
    script = f"""
        import sys, site
        sys.path.insert(0, {str(tmp_path)!r})
        site.addsitedir({str(tmp_path)!r})
        import synth_marker
        assert synth_marker.MARKER == "vendored", synth_marker.__file__
        print("OK")
    """
    result = subprocess.run(
        [sys.executable, "-S", "-c", textwrap.dedent(script)],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def _make_synthetic_pth_package(tmp_path):
    """Mimics pywin32's real layout: a .pth file at the vendored-lib root
    that redirects into a nested subdirectory, where the actual importable
    module lives — not directly importable via a plain sys.path entry on
    the root alone."""
    (tmp_path / "synth.pth").write_text("synth_nested\n", encoding="utf-8")
    nested = tmp_path / "synth_nested"
    nested.mkdir()
    (nested / "synth_marker.py").write_text("MARKER = 'vendored'\n", encoding="utf-8")
