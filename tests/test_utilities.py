"""Tests for helpers in ytscripts.utilities."""

import ytscripts.utilities as utils


def test_latex_check_only_looks_up_the_executable(monkeypatch):
    """The check must not run latex, which waits for input with no arguments."""
    looked_up = []

    def fake_which(name):
        looked_up.append(name)
        return None

    monkeypatch.setattr(utils.shutil, "which", fake_which)
    assert utils.is_latex_available() is False
    assert looked_up == ["latex"]

    monkeypatch.setattr(utils.shutil, "which", lambda name: "/usr/bin/latex")
    assert utils.is_latex_available() is True
