"""The version must be one number, not three that agree by hand.

`geopalette.__version__` reported 0.4.0 while `pyproject.toml` said 0.6.0.
Two releases were cut in between and both missed it, because the bump was
done by editing the places someone remembered rather than by searching for
the old number. Anyone importing the package from a source checkout and
reporting `geopalette.__version__` in a bug report was two releases out.

Copyright (C) 2025 Igor Pawelec. Licence: GPLv3.
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _pyproject_version():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    assert m, "no version in pyproject.toml"
    return m.group(1)


def test_dunder_version_matches_pyproject():
    import geopalette
    assert geopalette.__version__ == _pyproject_version(), (
        f"geopalette.__version__ is {geopalette.__version__} but "
        f"pyproject.toml says {_pyproject_version()}. Bump both."
    )


def test_citation_matches_pyproject():
    p = ROOT / "CITATION.cff"
    if not p.exists():
        pytest.skip("no CITATION.cff")
    m = re.search(r'(?m)^version:\s*"?([^"\n]+)"?\s*$', p.read_text(encoding="utf-8"))
    assert m, "no version in CITATION.cff"
    assert m.group(1).strip() == _pyproject_version(), (
        f"CITATION.cff says {m.group(1).strip()}, pyproject.toml says "
        f"{_pyproject_version()}. The CITATION is what a DOI cites."
    )


def test_changelog_documents_this_version():
    """A release with no changelog entry is a release nobody can read."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    version = _pyproject_version()
    assert re.search(rf"(?m)^#+\s*\[?{re.escape(version)}\]?", text), (
        f"CHANGELOG.md has no heading for {version}."
    )


def test_the_check_can_fail():
    """Guards the three above: a regex that never matches passes silently."""
    assert _pyproject_version() != "0.0.0"
    assert re.match(r"^\d+\.\d+\.\d+", _pyproject_version()), _pyproject_version()
