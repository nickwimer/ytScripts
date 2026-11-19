"""Tests for slice_plot: LaTeX settings, contours and the layout of the image."""

import tomllib
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
import yt

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


# Each axis of the test domain has its own length, so an image's extent shows which
# axes it is drawn with
BBOX = {"x": (0.0, 1.0), "y": (0.0, 2.0), "z": (0.0, 3.0)}
DIMS = {"x": 4, "y": 6, "z": 8}

# The axes yt draws across and up the image, before any swap
YT_AXES = {"x": ("y", "z"), "y": ("z", "x"), "z": ("x", "y")}

# (normal, axis across the image, axis up the image)
ORIENTATIONS = [("x", "y", "z"), ("y", "x", "z"), ("z", "x", "y")]


@pytest.fixture(scope="module")
def configs():
    with open(Path(sp.__file__).with_name("config.toml"), "rb") as f:
        return tomllib.load(f)


@pytest.fixture(scope="module")
def position_ds():
    """Return a uniform grid whose fields hold the position of each cell.

    pos_x, pos_y and pos_z are the cell-center coordinates, and the EB-style fields
    ("boxlib", "frac_x") and so on run from 0 to 1 along their axis.
    """
    centers = [
        lo + (np.arange(DIMS[axis]) + 0.5) * (hi - lo) / DIMS[axis]
        for axis, (lo, hi) in BBOX.items()
    ]
    data = {}
    for axis, pos in zip("xyz", np.meshgrid(*centers, indexing="ij")):
        lo, hi = BBOX[axis]
        data[f"pos_{axis}"] = (pos, "")
        data[("boxlib", f"frac_{axis}")] = ((pos - lo) / (hi - lo), "")
    ds = yt.load_uniform_grid(
        data,
        tuple(DIMS.values()),
        length_unit="cm",
        bbox=np.array(list(BBOX.values())),
    )
    # Let yt read the fields typed like those of a plotfile
    ds.fluid_types += ("boxlib",)
    return ds


def draw(ds, configs, options, field, eb_var_name="vfrac"):
    """Draw a slice plot of ds the way main() does; return the image axes."""
    args = sp.get_parser().get_args(["--datapath", ".", "--no_time", *options])
    pbox = args["pbox"]
    fig = sp.create_slice_plot(
        ds=ds,
        args=args,
        configs=configs,
        slc_center=ds.domain_center,
        vis_field=field,
        axes_unit="cm",
        pbox_width=(
            None
            if pbox is None
            else ((pbox[2] - pbox[0], "cm"), (pbox[3] - pbox[1], "cm"))
        ),
        pbox_center=(
            None if pbox is None else [(pbox[0] + pbox[2]) / 2, (pbox[1] + pbox[3]) / 2]
        ),
        eb_var_name=eb_var_name,
    )
    ax = fig.axes[0]
    plt.close(fig)
    return ax


@pytest.mark.parametrize("normal, across, up", ORIENTATIONS)
def test_image_axes(normal, across, up):
    assert sp.image_axes(normal) == (across, up, YT_AXES[normal] != (across, up))


def test_image_axes_needs_a_coordinate_normal():
    with pytest.raises(ValueError, match="x, y or z"):
        sp.image_axes("w")


@pytest.mark.parametrize("normal, across, up", ORIENTATIONS)
def test_image_contours_and_labels_follow_the_axes(
    position_ds, configs, normal, across, up
):
    """Draw the across position, with a contour of the up position on it."""
    level = sum(BBOX[up]) / 2
    ax = draw(
        position_ds,
        configs,
        ["--normal", normal, "--no_units", "--contour", f"pos_{up}", str(level), "w"],
        field=f"pos_{across}",
    )

    image = ax.get_images()[0]
    np.testing.assert_allclose(image.get_extent(), (*BBOX[across], *BBOX[up]))
    values = np.asarray(image.get_array())
    # Rows run up the image, so the across position changes only along a row
    assert np.all(np.diff(values, axis=1) >= 0)
    assert values[0, -1] > values[0, 0]
    np.testing.assert_allclose(values, np.broadcast_to(values[:1], values.shape))

    # One pixel per cell, in a square buffer if yt swaps the axes
    if YT_AXES[normal] == (across, up):
        assert values.shape == (DIMS[up], DIMS[across])
    else:
        assert values.shape == (max(DIMS[up], DIMS[across]),) * 2

    assert ax.get_xlabel() == f"${across}$"
    assert ax.get_ylabel() == f"${up}$"

    # A contour of the up position is a line across the image at that height
    lines = ax.get_lines()
    assert lines
    cell = max((hi - lo) / DIMS[axis] for axis, (lo, hi) in BBOX.items())
    for line in lines:
        np.testing.assert_allclose(line.get_ydata(), level, atol=cell / 2)
    assert (
        np.ptp(np.concatenate([line.get_xdata() for line in lines]))
        > (BBOX[across][1] - BBOX[across][0]) / 2
    )


@pytest.mark.parametrize("normal, across, up", ORIENTATIONS)
def test_pbox_is_given_across_then_up(position_ds, configs, normal, across, up):
    (a0, a1), (u0, u1) = BBOX[across], BBOX[up]
    pbox = [a0 + 0.25 * (a1 - a0), u0 + 0.5 * (u1 - u0), a1, u1]
    ax = draw(
        position_ds,
        configs,
        ["--normal", normal, "--pbox", *map(str, pbox)],
        field=f"pos_{across}",
    )

    image = ax.get_images()[0]
    np.testing.assert_allclose(image.get_extent(), [pbox[0], pbox[2], pbox[1], pbox[3]])
    values = np.asarray(image.get_array())
    cell = (a1 - a0) / DIMS[across]
    assert values.min() > pbox[0] - cell
    assert values.max() < pbox[2] + cell


@pytest.mark.parametrize("normal, across, up", ORIENTATIONS)
def test_rm_eb_covers_the_image_as_drawn(position_ds, configs, normal, across, up):
    """With frac_<across> as the volume fraction, the cover is the left half."""
    ax = draw(
        position_ds,
        configs,
        ["--normal", normal, "--rm_eb", "1"],
        field=f"pos_{across}",
        eb_var_name=f"frac_{across}",
    )

    image, cover = ax.get_images()
    np.testing.assert_allclose(cover.get_extent(), image.get_extent())
    covered = ~np.ma.getmaskarray(cover.get_array())
    assert covered.shape == np.shape(image.get_array())
    np.testing.assert_array_equal(covered, np.broadcast_to(covered[:1], covered.shape))
    assert covered[0, 0] and not covered[0, -1]


@pytest.mark.parametrize("normal, across, up", ORIENTATIONS)
def test_grid_info_is_placed_in_image_coordinates(
    position_ds, configs, normal, across, up
):
    position = (sum(BBOX[across]) / 2, sum(BBOX[up]) / 2)
    ax = draw(
        position_ds,
        configs,
        ["--normal", normal, "--grid_info", *map(str, position), "0", "0"],
        field=f"pos_{across}",
    )

    (text,) = [t for t in ax.texts if "DOF" in t.get_text()]
    assert text.get_position() == position
