"""Tests for slice_plot: LaTeX settings and placing contours on the drawn image."""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

import quick_vis.slice_plot as sp


def test_importing_leaves_latex_off():
    """LaTeX must not switch on by itself, even where it is installed."""
    assert plt.rcParams["text.usetex"] is False


def test_latex_only_when_asked_for(monkeypatch, capsys):
    with matplotlib.rc_context():
        monkeypatch.setattr(sp.utils, "is_latex_available", lambda: True)
        assert sp.configure_tex(False) is False
        assert plt.rcParams["text.usetex"] is False

        assert sp.configure_tex(True) is True
        assert plt.rcParams["text.usetex"] is True

    with matplotlib.rc_context():
        monkeypatch.setattr(sp.utils, "is_latex_available", lambda: False)
        assert sp.configure_tex(True) is False
        assert plt.rcParams["text.usetex"] is False
        assert "LaTeX was not found" in capsys.readouterr().out


def pixel_centers(extent, shape):
    """Return the horizontal and vertical pixel-center positions of an image."""
    left, right, bottom, top = extent
    nrows, ncols = shape
    h = left + (np.arange(ncols) + 0.5) * (right - left) / ncols
    v = bottom + (np.arange(nrows) + 0.5) * (top - bottom) / nrows
    return np.meshgrid(h, v)


def test_contours_land_where_the_field_has_the_level():
    # A non-square image of a region away from the origin, like --pbox or --buff
    extent = (-1.0, 3.0, 10.0, 12.0)
    hh, vv = pixel_centers(extent, (5, 8))

    # The image holds its own horizontal position, so the level 0.6 contour is
    # the vertical line h = 0.6
    lines = sp.contour_lines(hh, 0.6, extent)
    assert lines
    for line in lines:
        np.testing.assert_allclose(line[:, 0], 0.6)
        assert np.all((line[:, 1] >= 10.0) & (line[:, 1] <= 12.0))

    # Likewise a vertical position field gives the horizontal line v = 11.3
    lines = sp.contour_lines(vv, 11.3, extent)
    assert lines
    for line in lines:
        np.testing.assert_allclose(line[:, 1], 11.3)


def test_contour_level_may_be_given_as_text():
    """--contour passes the level through as a string."""
    extent = (0.0, 1.0, 0.0, 1.0)
    hh, _ = pixel_centers(extent, (4, 4))
    lines = sp.contour_lines(hh, "0.5", extent)
    np.testing.assert_allclose(lines[0][:, 0], 0.5)
