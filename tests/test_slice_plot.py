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

# (--normal, --up or None, axis across the image, axis up the image)
ORIENTATIONS = [
    ("x", None, "y", "z"),
    ("x", "z", "y", "z"),
    ("x", "y", "z", "y"),
    ("y", None, "x", "z"),
    ("y", "z", "x", "z"),
    ("y", "x", "z", "x"),
    ("z", None, "x", "y"),
    ("z", "y", "x", "y"),
    ("z", "x", "y", "x"),
]


def orientation(normal, up_arg):
    """Return the command line options for --normal and, if given, --up."""
    return ["--normal", normal] + ([] if up_arg is None else ["--up", up_arg])


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


@pytest.mark.parametrize("normal, up_arg, across, up", ORIENTATIONS)
def test_image_axes(normal, up_arg, across, up):
    assert sp.image_axes(normal, up_arg) == (
        across,
        up,
        YT_AXES[normal] != (across, up),
    )


def test_image_axes_needs_a_coordinate_normal():
    with pytest.raises(ValueError, match="x, y or z"):
        sp.image_axes("w")


def test_image_axes_up_must_be_an_axis_of_the_slice():
    with pytest.raises(ValueError, match="y or z for normal x"):
        sp.image_axes("x", "x")


def test_up_defaults_to_none_and_takes_only_axes():
    assert sp.get_parser().get_args(["--datapath", "."])["up"] is None
    with pytest.raises(SystemExit):
        sp.get_parser().get_args(["--datapath", ".", "--up", "w"])


@pytest.mark.parametrize("normal", ["x", "y", "z"])
def test_up_along_the_normal_is_a_usage_error(normal, capsys):
    with pytest.raises(SystemExit) as error:
        sp.get_parser().get_args(
            ["--datapath", ".", "--normal", normal, "--up", normal]
        )
    assert error.value.code == 2
    in_slice = " or ".join(axis for axis in "xyz" if axis != normal)
    message = capsys.readouterr().err
    assert f"--up {normal} points along --normal {normal}" in message
    assert message.rstrip().endswith(in_slice)


def test_up_may_come_from_the_input_file(tmp_path, capsys):
    ifile = tmp_path / "plot.toml"
    ifile.write_text('normal = "x"\nup = "y"\n')
    args = sp.get_parser().get_args(["--datapath", ".", "--ifile", str(ifile)])
    assert (args["normal"], args["up"]) == ("x", "y")

    # The input file is checked too
    ifile.write_text('normal = "z"\nup = "z"\n')
    with pytest.raises(SystemExit):
        sp.get_parser().get_args(["--datapath", ".", "--ifile", str(ifile)])
    assert "--up z points along --normal z" in capsys.readouterr().err


@pytest.mark.parametrize("normal, up_arg, across, up", ORIENTATIONS)
def test_image_contours_and_labels_follow_the_axes(
    position_ds, configs, normal, up_arg, across, up
):
    """Draw the across position, with a contour of the up position on it."""
    level = sum(BBOX[up]) / 2
    ax = draw(
        position_ds,
        configs,
        [
            *orientation(normal, up_arg),
            "--no_units",
            "--contour",
            f"pos_{up}",
            str(level),
            "w",
        ],
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


@pytest.mark.parametrize("normal, up_arg, across, up", ORIENTATIONS)
def test_pbox_is_given_across_then_up(position_ds, configs, normal, up_arg, across, up):
    (a0, a1), (u0, u1) = BBOX[across], BBOX[up]
    pbox = [a0 + 0.25 * (a1 - a0), u0 + 0.5 * (u1 - u0), a1, u1]
    ax = draw(
        position_ds,
        configs,
        [*orientation(normal, up_arg), "--pbox", *map(str, pbox)],
        field=f"pos_{across}",
    )

    image = ax.get_images()[0]
    np.testing.assert_allclose(image.get_extent(), [pbox[0], pbox[2], pbox[1], pbox[3]])
    values = np.asarray(image.get_array())
    cell = (a1 - a0) / DIMS[across]
    assert values.min() > pbox[0] - cell
    assert values.max() < pbox[2] + cell


@pytest.mark.parametrize("normal, up_arg, across, up", ORIENTATIONS)
def test_rm_eb_covers_the_image_as_drawn(
    position_ds, configs, normal, up_arg, across, up
):
    """With frac_<across> as the volume fraction, the cover is the left half."""
    ax = draw(
        position_ds,
        configs,
        [*orientation(normal, up_arg), "--rm_eb", "1"],
        field=f"pos_{across}",
        eb_var_name=f"frac_{across}",
    )

    image, cover = ax.get_images()
    np.testing.assert_allclose(cover.get_extent(), image.get_extent())
    covered = ~np.ma.getmaskarray(cover.get_array())
    assert covered.shape == np.shape(image.get_array())
    np.testing.assert_array_equal(covered, np.broadcast_to(covered[:1], covered.shape))
    assert covered[0, 0] and not covered[0, -1]


@pytest.mark.parametrize("normal, up_arg, across, up", ORIENTATIONS)
def test_grid_info_is_placed_in_image_coordinates(
    position_ds, configs, normal, up_arg, across, up
):
    position = (sum(BBOX[across]) / 2, sum(BBOX[up]) / 2)
    ax = draw(
        position_ds,
        configs,
        [*orientation(normal, up_arg), "--grid_info", *map(str, position), "0", "0"],
        field=f"pos_{across}",
    )

    (text,) = [t for t in ax.texts if "DOF" in t.get_text()]
    assert text.get_position() == position


R = np.sqrt(0.5)

# (--normal, --up or None, unit vector across the image, unit vector up it, its
# labels, and the image extent as positions along those directions). The slice goes
# through the domain center (0.5, 1, 1.5): for xz that is the plane x + z = 2, where
# (x - z)/sqrt(2) runs from -sqrt(2) to 0 and y from 0 to 2.
DIAGONALS = [
    ("xz", None, (R, 0, -R), (0, 1, 0), (r"(x - z)/\sqrt{2}", "y"), (-2 * R, 0, 0, 2)),
    ("z-x", None, (R, 0, R), (0, 1, 0), (r"(x + z)/\sqrt{2}", "y"), (R, 3 * R, 0, 2)),
    (
        "yz",
        None,
        (0, -R, R),
        (1, 0, 0),
        (r"(z - y)/\sqrt{2}", "x"),
        (-1.5 * R, 2.5 * R, 0, 1),
    ),
    (
        "xz",
        "x",
        (0, -1, 0),
        (R, 0, -R),
        ("-y", r"(x - z)/\sqrt{2}"),
        (-2, 0, -2 * R, 0),
    ),
]


@pytest.mark.parametrize("normal, up_arg, across, up, labels, extent", DIAGONALS)
def test_diagonal_slices_are_drawn_across_and_up(
    position_ds, configs, normal, up_arg, across, up, labels, extent
):
    for axis, a, u in zip("xyz", across, up):
        ax = draw(position_ds, configs, orientation(normal, up_arg), f"pos_{axis}")
        image = ax.get_images()[0]
        np.testing.assert_allclose(image.get_extent(), extent, atol=1e-12)
        values = np.asarray(image.get_array())
        assert np.isfinite(values).all()

        # Each position changes across and up the image as that direction says
        for direction, part in ((1, a), (0, u)):
            steps = np.diff(values, axis=direction)
            if part == 0:
                np.testing.assert_allclose(steps, 0)
            else:
                assert np.all(np.sign(part) * steps >= 0)
                assert np.sign(part) * steps.sum() > 0

    assert ax.get_xlabel() == f"${labels[0]}$ (cm)"
    assert ax.get_ylabel() == f"${labels[1]}$ (cm)"


def test_diagonal_slice_without_units_and_with_a_contour(position_ds, configs):
    ax = draw(
        position_ds,
        configs,
        ["--normal", "xz", "--no_units", "--contour", "pos_y", "1.3", "w"],
        field="pos_x",
    )
    assert ax.get_xlabel() == r"$(x - z)/\sqrt{2}$"
    assert ax.get_ylabel() == "$y$"

    # pos_y = 1.3 runs straight across the image at y = 1.3
    lines = ax.get_lines()
    assert lines
    cell = BBOX["y"][1] / DIMS["y"]
    for line in lines:
        np.testing.assert_allclose(line.get_ydata(), 1.3, atol=cell / 2)
    assert np.ptp(np.concatenate([line.get_xdata() for line in lines])) > R


def test_diagonal_pbox_is_positions_along_the_image(position_ds, configs):
    """--pbox takes (x - z)/sqrt(2) across and y up for xz, like the axes show."""
    pbox = [-1.2, 0.5, -0.2, 1.25]
    options = ["--normal", "xz", "--pbox", *map(str, pbox)]
    for axis, lo, hi in (
        # On x + z = 2, x = 1 + (x - z)/2 = 1 + R (x - z)/sqrt(2)
        ("x", 1 + R * pbox[0], 1 + R * pbox[2]),
        ("y", pbox[1], pbox[3]),
    ):
        image = draw(position_ds, configs, options, f"pos_{axis}").get_images()[0]
        np.testing.assert_allclose(
            image.get_extent(), [pbox[0], pbox[2], pbox[1], pbox[3]]
        )
        values = np.asarray(image.get_array())
        cell = (BBOX[axis][1] - BBOX[axis][0]) / DIMS[axis]
        assert values.min() > lo - cell and values.max() < hi + cell


def test_diagonal_image_is_blank_off_the_domain(position_ds, configs):
    ax = draw(
        position_ds,
        configs,
        # (x - z)/sqrt(2) only reaches 0, so the right half is off the domain
        ["--normal", "xz", "--pbox", "-1", "0", "1", "2", "--rm_eb", "1"],
        field="pos_y",
        eb_var_name="frac_x",
    )
    image, cover = ax.get_images()
    blank = ~np.isfinite(np.ma.filled(image.get_array().astype(float), np.nan))
    assert blank.any() and not blank.all()
    # The EB cover leaves the area off the domain alone
    assert np.ma.getmaskarray(cover.get_array())[blank].all()


def test_rm_eb_on_a_diagonal_slice(position_ds, configs):
    """With frac_x as the volume fraction, the cover is where x < 0.5: the left."""
    ax = draw(
        position_ds,
        configs,
        ["--normal", "xz", "--rm_eb", "1"],
        field="pos_x",
        eb_var_name="frac_x",
    )
    image, cover = ax.get_images()
    np.testing.assert_allclose(cover.get_extent(), image.get_extent())
    covered = ~np.ma.getmaskarray(cover.get_array())
    assert covered[0, 0] and not covered[0, -1]


def test_grids_are_skipped_on_a_diagonal_slice(position_ds, configs, capsys):
    ax = draw(position_ds, configs, ["--normal", "xz", "--grids", "0.5"], "pos_x")
    assert ax.get_images()
    assert "--grids is not available for diagonal slices" in capsys.readouterr().out


def test_cells_are_skipped_on_a_diagonal_slice(position_ds, configs, capsys):
    ax = draw(
        position_ds,
        configs,
        ["--normal", "xz", "--cells", "0.002", "0.5", "k"],
        "pos_x",
    )
    # Only the slice itself: no cell edge overlay
    assert len(ax.get_images()) == 1
    assert "--cells is not available for diagonal slices" in capsys.readouterr().out


def test_diagonal_slice_center_is_checked_first(
    position_ds, tmp_path, monkeypatch, capsys
):
    """A --center whose diagonal plane misses the domain is a usage error."""

    class SeriesNotRead(list):
        def piter(self, *args, **kwargs):
            raise AssertionError("the plotfiles were read before the slice was checked")

    monkeypatch.setattr(
        sp.utils, "load_dataseries", lambda **kwargs: (SeriesNotRead([position_ds]), {})
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            # main() reads config.toml next to the script
            sp.__file__,
            *("--datapath", ".", "--field", "pos_x", "--normal", "xz"),
            *("--center", "5", "1", "5", "--outpath", str(tmp_path)),
        ],
    )
    with pytest.raises(SystemExit):
        sp.main()
    assert "misses the domain" in capsys.readouterr().err


def test_contours_skip_blank_pixels():
    extent = (0.0, 1.0, 0.0, 1.0)
    hh, _ = pixel_centers(extent, (4, 4))
    hh[:, -1] = np.nan
    lines = sp.contour_lines(hh, 0.5, extent)
    assert lines
    for line in lines:
        np.testing.assert_allclose(line[:, 0], 0.5)
