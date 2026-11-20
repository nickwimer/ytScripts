"""Tests for the slice, average, line, isosurface and threshold extraction helpers."""

import h5py
import matplotlib
import numpy as np
import pandas as pd
import pytest
import yt
from skimage.measure import marching_cubes

import data_extraction.extract_averages as averages
import data_extraction.extract_isosurfaces as iso
import data_extraction.extract_lines as lines
import data_extraction.extract_slices as extract_slices
import data_extraction.extract_threshold as threshold
import plot_data.plot_slices as plot_slices
import ytscripts.utilities as utils

# Every script needs --datapath; the parser only checks that it is set
DATA = ["--datapath", "."]


def test_lines_with_different_cells_line_up_by_position():
    """With AMR the cells along the line change between times."""
    coarse = (np.array([0.75, 0.25]), np.array([30.0, 10.0]), {})
    refined = (np.array([0.125, 0.375, 0.75]), np.array([1.0, 2.0, 3.0]), {})
    df = lines.lines_to_dataframe({2.0: refined, 1.0: coarse}, "x")

    assert list(df.columns) == [1.0, 2.0]
    assert list(df.index) == [0.125, 0.25, 0.375, 0.75]
    assert df.index.name == "x"
    assert df.loc[0.25, 1.0] == 10.0
    assert df.loc[0.75, 1.0] == 30.0
    assert df.loc[0.75, 2.0] == 3.0
    assert np.isnan(df.loc[0.25, 2.0])


def test_line_args_need_field_and_two_coords():
    parser = lines.get_parser()
    with pytest.raises(SystemExit):
        lines.get_args(parser, [*DATA, "--coords", "0", "0"])
    with pytest.raises(SystemExit):
        lines.get_args(parser, [*DATA, "--field", "temp", "--coords", "0"])

    args = lines.get_args(
        parser, [*DATA, "--field", "temp", "--coords", "0", "-1", "--normal", "x"]
    )
    assert args["coords"] == [0.0, -1.0]
    assert args["normal"] == "x"


def test_diagonal_line_args_need_a_point(capsys):
    parser = lines.get_parser()
    with pytest.raises(SystemExit):
        lines.get_args(
            parser, [*DATA, "--field", "temp", "--coords", "0", "1", "--normal", "xz"]
        )
    assert "--coords needs three values" in capsys.readouterr().err

    args = lines.get_args(
        lines.get_parser(),
        [*DATA, "--field", "temp", "--coords", "0", "1", "2", "--normal", "x-z"],
    )
    assert args["coords"] == [0.0, 1.0, 2.0]
    assert args["normal"] == "x-z"


def test_line_coords_from_input_file_must_be_two_values(tmp_path):
    ifile = tmp_path / "line.toml"
    ifile.write_text('field = "temp"\ncoords = [0.0, 1.0, 2.0]\n')
    with pytest.raises(SystemExit):
        lines.get_args(lines.get_parser(), ["--ifile", str(ifile)])


def test_extra_fields_sampled_at_vertices():
    spacing = (0.5, 0.25, 2.0)
    i, j, k = np.meshgrid(np.arange(12), np.arange(10), np.arange(8), indexing="ij")
    x, y, z = i * spacing[0], j * spacing[1], k * spacing[2]
    sphere = (x - 3) ** 2 + (y - 1.2) ** 2 + (z - 7) ** 2
    linear = 2 * x - y + 0.5 * z

    verts, _, _, _ = marching_cubes(sphere, level=4.0, spacing=spacing)

    # marching_cubes returns float32 vertices, so compare at that precision.
    # The isosurface field itself comes back as the iso value at every vertex.
    np.testing.assert_allclose(
        iso.sample_at_vertices(sphere, verts, spacing), 4.0, rtol=1e-5
    )
    # A linear field is reproduced exactly at the vertex positions
    expected = 2 * verts[:, 0] - verts[:, 1] + 0.5 * verts[:, 2]
    np.testing.assert_allclose(
        iso.sample_at_vertices(linear, verts, spacing), expected, rtol=1e-5
    )


def test_ghost_padding_stays_inside_the_domain():
    level_dims = [16, 16, 16]
    # Interior grid: one ghost layer on every side
    low, high = iso.ghost_padding([4, 4, 4], [8, 8, 8], level_dims, 1)
    assert list(low) == [1, 1, 1] and list(high) == [1, 1, 1]

    # Touching the low and high domain edges: no ghost cells past them
    low, high = iso.ghost_padding([0, 4, 8], [8, 8, 8], level_dims, 1)
    assert list(low) == [0, 1, 1] and list(high) == [1, 1, 0]

    # One cell in from either edge: the ghost layer still fits (this was skipped)
    low, high = iso.ghost_padding([1, 4, 4], [8, 8, 11], level_dims, 1)
    assert list(low) == [1, 1, 1] and list(high) == [1, 1, 1]


def test_extra_fields_need_hdf5_or_xdmf_output(capsys):
    parser = iso.get_parser()
    with pytest.raises(SystemExit):
        iso.get_args(parser, [*DATA, "--value", "1", "--extra_fields", "rho"])
    assert "--extra_fields needs --format hdf5 or xdmf" in capsys.readouterr().err

    args = iso.get_args(
        iso.get_parser(),
        [*DATA, "--value", "1", "--format", "xdmf", "--extra_fields", "rho", "temp"],
    )
    assert args["extra_fields"] == ["rho", "temp"]


# Each axis of the test domain has its own length
BBOX = {"x": (0.0, 1.0), "y": (0.0, 2.0), "z": (0.0, 3.0)}
DIMS = {"x": 4, "y": 6, "z": 8}
R = np.sqrt(0.5)


@pytest.fixture(scope="module")
def position_ds():
    """Return a uniform grid whose fields pos_x, pos_y and pos_z hold the position."""
    centers = [
        lo + (np.arange(DIMS[axis]) + 0.5) * (hi - lo) / DIMS[axis]
        for axis, (lo, hi) in BBOX.items()
    ]
    data = {
        f"pos_{axis}": (pos, "")
        for axis, pos in zip("xyz", np.meshgrid(*centers, indexing="ij"))
    }
    data["unity"] = (np.ones(tuple(DIMS.values())), "")
    return yt.load_uniform_grid(
        data,
        tuple(DIMS.values()),
        length_unit="cm",
        bbox=np.array(list(BBOX.values())),
    )


def test_line_ends_clip_to_the_box():
    start, end = lines.line_ends((0, 0, 0), (1, 2, 3), (R, 0, R), (0.5, 1.0, 1.5))
    np.testing.assert_allclose(start, (0, 1, 1), atol=1e-12)
    np.testing.assert_allclose(end, (1, 1, 2), atol=1e-12)

    with pytest.raises(ValueError, match="misses the domain"):
        lines.line_ends((0, 0, 0), (1, 2, 3), (R, 0, R), (0.5, 5.0, 1.5))
    with pytest.raises(ValueError, match="misses the domain"):
        lines.line_ends((0, 0, 0), (1, 2, 3), (R, 0, -R), (5.0, 1.0, 5.0))


def test_diagonal_line_positions_are_distances_along_it(position_ds):
    positions, ray = lines.take_line(position_ds, "xz", [0.5, 1.0, 1.5])
    positions = np.asarray(positions)
    # From (0, 1, 1) to (1, 1, 2): (x + z)/sqrt(2) runs from 1/sqrt(2) to 3/sqrt(2)
    assert positions.min() > R and positions.max() < 3 * R
    # Each cell holds the line where it passes: x and z rise along it, y stays
    order = np.argsort(positions)
    for axis in "xz":
        assert np.all(np.diff(np.asarray(ray[f"pos_{axis}"])[order]) >= 0)
    np.testing.assert_allclose(ray["pos_y"], 7 / 6)
    np.testing.assert_allclose(
        positions,
        R * (np.asarray(ray["pos_x"]) + np.asarray(ray["pos_z"])),
        atol=np.hypot(0.125, 0.1875) + 1e-9,
    )


def test_axis_line_is_unchanged(position_ds):
    positions, ray = lines.take_line(position_ds, "x", [1.0, 1.5])
    np.testing.assert_allclose(positions, [0.125, 0.375, 0.625, 0.875])
    np.testing.assert_allclose(ray["pos_x"], positions)


def test_diagonal_slice_extraction(position_ds):
    normal, across, up = utils.slice_basis("xz")
    attributes = utils.get_attributes(position_ds)
    _, frb, plane = extract_slices.cut_plane(
        position_ds, attributes, normal, across, up, 1.0
    )
    assert plane["center"] @ normal == pytest.approx(1.0)
    # On x + z = sqrt(2), x runs from 0 to 1, so (x - z)/sqrt(2) = sqrt(2) x - 1
    np.testing.assert_allclose(plane["bounds"], (-1, np.sqrt(2) - 1, 0, 2))

    pos = {axis: np.asarray(frb[f"pos_{axis}"]) for axis in "xyz"}
    assert all(np.isfinite(image).all() for image in pos.values())
    # Rows run up (y), columns across ((x - z)/sqrt(2)), all on x + z = sqrt(2)
    assert np.all(np.diff(pos["y"], axis=0) >= 0) and pos["y"][-1, 0] > pos["y"][0, 0]
    np.testing.assert_allclose(np.diff(pos["y"], axis=1), 0)
    assert np.all(np.diff(pos["x"] - pos["z"], axis=1) >= 0)
    np.testing.assert_allclose(R * (pos["x"] + pos["z"]), 1.0, atol=0.3)

    with pytest.raises(ValueError, match="misses the domain"):
        extract_slices.cut_plane(position_ds, attributes, normal, across, up, 3.0)


def test_diagonal_slice_average(position_ds):
    data = position_ds.all_data()
    plane = averages.slice_data(position_ds, data, "xz", 2.0 * R)
    weight = ("index", "cell_volume")
    assert float(plane.mean("unity", weight=weight)) == pytest.approx(1.0)
    # x + z is about 2 on the plane, and y covers its whole range
    assert float(plane.mean("pos_y", weight=weight)) == pytest.approx(1.0)
    x_plus_z = float(plane.mean("pos_x", weight=weight)) + float(
        plane.mean("pos_z", weight=weight)
    )
    assert x_plus_z == pytest.approx(2.0, abs=0.2)

    # An axis normal is a plain slice
    plane = averages.slice_data(position_ds, data, "x", 0.6)
    np.testing.assert_allclose(plane["pos_x"], 0.625)


class SeriesNotRead(list):
    """A dataset series whose plotfiles must not be looped over."""

    def piter(self, *args, **kwargs):
        raise AssertionError("the plotfiles were read before the slice was checked")


@pytest.mark.parametrize(
    "span, message",
    [
        (["--min", "0.5", "--max", "3.0"], "misses"),
        (["--min", "0", "--max", "1"], "only touches"),
    ],
)
def test_slice_distances_are_checked_first(
    position_ds, tmp_path, monkeypatch, capsys, span, message
):
    """x + z spans 0 to 4 on the test domain, so the distance spans 0 to 2.83."""
    monkeypatch.setattr(
        utils, "load_dataseries", lambda **kwargs: (SeriesNotRead([position_ds]), {})
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "extract_slices.py",
            *DATA,
            *("--field", "pos_y", "--normal", "xz", "--num_slices", "3"),
            *span,
            *("--outpath", str(tmp_path)),
        ],
    )
    with pytest.raises(SystemExit):
        extract_slices.main()
    err = capsys.readouterr().err
    assert "--min/--max" in err and message in err
    assert not list(tmp_path.iterdir())


def test_average_location_is_checked_first(position_ds, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        utils, "load_dataseries", lambda **kwargs: (SeriesNotRead([position_ds]), {})
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "extract_averages.py",
            *DATA,
            *("--fields", "pos_x", "--normal", "xz", "--location", "5"),
            *("--outpath", str(tmp_path)),
        ],
    )
    with pytest.raises(SystemExit):
        averages.main()
    err = capsys.readouterr().err
    assert "--location" in err and "misses the domain" in err


def test_plot_a_diagonal_slice(position_ds, tmp_path, monkeypatch):
    normal, across, up = utils.slice_basis("xz")
    attributes = utils.get_attributes(position_ds)
    _, frb, plane = extract_slices.cut_plane(
        position_ds, attributes, normal, across, up, 2.0 * R
    )
    plane["labels"] = np.array(
        [utils.direction_label(across), utils.direction_label(up)]
    )
    datapath = tmp_path / "slices"
    datapath.mkdir()
    np.savez(
        datapath / "pos_y_xz1.4142_0.npz",
        fcoords=np.zeros((1, 3)),
        normal="xz",
        iloc=2.0 * R,
        fields="pos_y",
        slices={"pos_y": frb["pos_y"]},
        ds_attributes=attributes,
        **plane,
    )

    data = np.load(datapath / "pos_y_xz1.4142_0.npz", allow_pickle=True)
    ylen, xlen = data["slices"][()]["pos_y"].shape
    h, v, hlabel, vlabel, dh, dv, where = plot_slices.image_layout(data, xlen, ylen)
    # On x + z = 2, (x - z)/sqrt(2) runs from -sqrt(2) to 0 and y from 0 to 2
    np.testing.assert_allclose([h[0] - dh / 2, h[-1] + dh / 2], [-2 * R, 0], atol=1e-12)
    np.testing.assert_allclose([v[0] - dv / 2, v[-1] + dv / 2], [0, 2])
    assert (hlabel, vlabel, where) == (r"$(x - z)/\sqrt{2}$", "$y$", "xz: d")

    matplotlib.use("Agg")
    outpath = tmp_path / "images"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plot_slices.py",
            "--datapath",
            str(datapath),
            "--outpath",
            str(outpath),
            "--field",
            "pos_y",
        ],
    )
    plot_slices.main()
    assert (outpath / "pos_y_xz1.4142_0.png").exists()


def test_threshold_mask_keeps_finest_cells_inside_the_band():
    values = np.array([0.5, 2.0, 3.0, 5.0, 2.5])
    child_mask = np.array([True, True, False, True, True])
    x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    coords = (x, np.zeros(5), np.zeros(5))

    mask = threshold.threshold_mask(values, child_mask, 1.0)
    assert list(mask) == [False, True, False, True, True]

    mask = threshold.threshold_mask(values, child_mask, 1.0, vmax=4.0)
    assert list(mask) == [False, True, False, False, True]

    bounds = (0.5, -1.0, -1.0, 3.5, 1.0, 1.0)
    mask = threshold.threshold_mask(
        values, child_mask, 1.0, coords=coords, bounds=bounds
    )
    assert list(mask) == [False, True, False, True, False]


def test_threshold_value_follows_the_function():
    vfunction = (1.0, 10.0, 3.0, 30.0)
    assert threshold.threshold_value(vfunction, 0.0) == 10.0
    assert threshold.threshold_value(vfunction, 2.0) == pytest.approx(20.0)
    assert threshold.threshold_value(vfunction, 4.0) == 30.0


@pytest.mark.parametrize(
    "extra, message",
    [
        (["--value", "1", "--max", "1"], "--max must be larger than --value"),
        (["--vfunction", "0", "1", "2"], "--vfunction needs four values"),
        (["--value", "1", "--bounds", "0", "0", "0", "1"], "--bounds needs six"),
        (
            ["--value", "1", "--bounds", "0", "0", "0", "1", "-1", "1"],
            "--bounds needs each low value below its high",
        ),
        (["--value", "1"], "--field"),
        (["--field", "temp"], "--value or --vfunction"),
    ],
)
def test_threshold_args_are_checked(capsys, extra, message):
    if "--field" not in extra and message != "--field":
        extra = ["--field", "temp", *extra]
    with pytest.raises(SystemExit):
        threshold.get_args(threshold.get_parser(), [*DATA, *extra])
    assert message in capsys.readouterr().err


@pytest.fixture(scope="module")
def amr_ds():
    """Return a two level dataset with heat = x + y + z on every level."""
    grids = []
    for level, left, right, n in [(0, 0.0, 1.0, 8), (1, 0.25, 0.75, 8)]:
        centers = left + (np.arange(n) + 0.5) * (right - left) / n
        x, y, z = np.meshgrid(centers, centers, centers, indexing="ij")
        grids.append(
            {
                "level": level,
                "left_edge": [left] * 3,
                "right_edge": [right] * 3,
                "dimensions": [n] * 3,
                "heat": (x + y + z, ""),
                "temp": (2.0 * x, ""),
            }
        )
    return yt.load_amr_grids(
        grids, [8, 8, 8], length_unit="cm", bbox=np.array([[0.0, 1.0]] * 3)
    )


@pytest.mark.parametrize("do_yt", [False, True])
def test_threshold_extraction_keeps_each_location_once(amr_ds, tmp_path, do_yt):
    ds_attributes = utils.get_attributes(amr_ds)
    comm = utils.SerialComm()
    ncells = threshold.do_threshold_extraction(
        dregion=amr_ds.all_data(),
        ds_attributes=ds_attributes,
        outformat="pkl",
        field="heat",
        value=1.5,
        outpath=str(tmp_path),
        fname="cells",
        comm=comm,
        rank=0,
        size=1,
        vmax=2.0,
        do_yt=do_yt,
        ds=amr_ds,
        extra_fields=["temp", "heat"],
    )

    df = pd.read_pickle(tmp_path / "cells.pkl")
    assert len(df) == ncells > 0
    assert list(df.columns) == [*threshold.CELL_COLUMNS, "heat", "temp"]
    assert df.attrs["field"] == "heat" and df.attrs["threshold"] == 1.5
    assert df.attrs["units"]["x"] == "cm"

    np.testing.assert_allclose(df["heat"], df["x"] + df["y"] + df["z"])
    np.testing.assert_allclose(df["temp"], 2.0 * df["x"])
    assert (df["heat"] > 1.5).all() and (df["heat"] < 2.0).all()
    assert set(df["level"]) == {0, 1}
    np.testing.assert_allclose(df["dx"], np.where(df["level"] == 0, 1 / 8, 1 / 16))

    # No coarse cell under the fine grid is kept
    coarse = df[df["level"] == 0]
    inside = np.all([(coarse[a] > 0.25) & (coarse[a] < 0.75) for a in "xyz"], axis=0)
    assert not inside.any()

    # The kept cells are every cell in the band, counted by brute force
    fine = (np.arange(8) + 0.5) / 16 + 0.25
    coarse_c = (np.arange(8) + 0.5) / 8
    fx, fy, fz = np.meshgrid(fine, fine, fine, indexing="ij")
    cx, cy, cz = np.meshgrid(coarse_c, coarse_c, coarse_c, indexing="ij")
    uncovered = ~np.all([(c > 0.25) & (c < 0.75) for c in (cx, cy, cz)], axis=0)
    fheat, cheat = fx + fy + fz, cx + cy + cz
    expected = np.count_nonzero((fheat > 1.5) & (fheat < 2.0)) + np.count_nonzero(
        uncovered & (cheat > 1.5) & (cheat < 2.0)
    )
    assert ncells == expected


def test_threshold_hdf5_and_xdmf_output(amr_ds, tmp_path):
    bounds = [0.0, 0.0, 0.0, 0.5, 1.0, 1.0]
    threshold.do_threshold_extraction(
        dregion=amr_ds.all_data(),
        ds_attributes=utils.get_attributes(amr_ds),
        outformat="xdmf",
        field="heat",
        value=1.0,
        outpath=str(tmp_path),
        fname="cells",
        comm=utils.SerialComm(),
        rank=0,
        size=1,
        bounds=bounds,
        extra_fields=["temp"],
    )

    with h5py.File(tmp_path / "cells.hdf5", "r") as f:
        coords = f["Coord"][()]
        assert coords.shape[1] == 3 and len(coords) > 0
        assert f["dds"].shape == coords.shape
        assert len(f["Level"]) == len(f["heat"]) == len(f["temp"]) == len(coords)
        assert (coords[:, 0] <= 0.5).all()
        assert (f["heat"][()] > 1.0).all()
        assert f.attrs["field"] == "heat" and f.attrs["threshold"] == 1.0
        np.testing.assert_allclose(f.attrs["bounds"], bounds)

    xmf = (tmp_path / "cells.xmf").read_text()
    assert 'TopologyType="Polyvertex"' in xmf
    assert f'NumberOfElements="{len(coords)}"' in xmf
    for name in ("Coord", "dds", "Level", "heat", "temp"):
        assert f"cells.hdf5:/{name}" in xmf
