"""Tests for the line and isosurface extraction helpers."""

import numpy as np
import pytest
from skimage.measure import marching_cubes

import data_extraction.extract_isosurfaces as iso
import data_extraction.extract_lines as lines

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
