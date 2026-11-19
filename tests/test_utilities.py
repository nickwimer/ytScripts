"""Tests for helpers in ytscripts.utilities."""

import numpy as np
import pytest

import ytscripts.utilities as utils


def species_attributes(*names):
    """Return a minimal dataset attributes dict with the given species fields."""
    return {"field_list": [("boxlib", f"Y({name})") for name in names]}


def test_elemental_mass_fractions():
    fracs, masses, fields = utils.compute_elem_mass_fraction(
        species_attributes("CH4", "CO2", "NC12H26", "N2", "AR")
    )
    assert len(fields) == 5

    # CH4: 12.01 of carbon in 16.01 total
    assert fracs["CH4"]["C"] == pytest.approx(12.01 / 16.01)
    assert fracs["CH4"]["H"] == pytest.approx(4.00 / 16.01)
    # CO2: 32 of oxygen in 44.01
    assert fracs["CO2"]["O"] == pytest.approx(32.00 / 44.01)
    # n-dodecane is stored without its leading N
    assert fracs["C12H26"]["C"] == pytest.approx(144.12 / 170.12)
    assert fracs["N2"]["N"] == pytest.approx(1.0)
    # Argon has none of these elements
    assert all(value == 0.0 for value in fracs["AR"].values())

    for spec in ("CH4", "CO2", "C12H26", "N2"):
        assert sum(fracs[spec].values()) == pytest.approx(1.0)


def test_elemental_mass_fractions_for_chosen_species():
    fracs, _, fields = utils.compute_elem_mass_fraction(
        species_attributes("CH4", "O2"), keys=["O2"]
    )
    assert list(fracs) == ["O2"]
    assert fields == [("boxlib", "Y(O2)")]
    assert fracs["O2"]["O"] == pytest.approx(1.0)


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


SQRT_HALF = np.sqrt(0.5)


@pytest.mark.parametrize(
    "name, vector",
    [
        ("x", (1, 0, 0)),
        ("z", (0, 0, 1)),
        ("xz", (SQRT_HALF, 0, SQRT_HALF)),
        ("x+z", (SQRT_HALF, 0, SQRT_HALF)),
        ("zx", (SQRT_HALF, 0, SQRT_HALF)),
        ("x-z", (SQRT_HALF, 0, -SQRT_HALF)),
        ("z-x", (-SQRT_HALF, 0, SQRT_HALF)),
        ("xy", (SQRT_HALF, SQRT_HALF, 0)),
        ("yz", (0, SQRT_HALF, SQRT_HALF)),
    ],
)
def test_normal_names_give_unit_vectors(name, vector):
    np.testing.assert_allclose(utils.parse_normal(name), vector)


@pytest.mark.parametrize("name", ["", "w", "xx", "x-x", "xw", "x-", "-x", "xyz", 1])
def test_bad_normal_names(name):
    with pytest.raises(ValueError, match="pair of different axes"):
        utils.parse_normal(name)


def test_standard_normal_names():
    assert utils.canonical_normal("x+z") == "xz"
    assert utils.canonical_normal("x-z") == "x-z"
    assert utils.canonical_normal("y") == "y"
    assert utils.is_axis_normal("y")
    assert not utils.is_axis_normal("xz")


@pytest.mark.parametrize(
    "name, up, across_label, up_label",
    [
        ("x", None, "y", "z"),
        ("z", None, "x", "y"),
        ("xz", None, r"(x - z)/\sqrt{2}", "y"),
        ("x-z", None, r"-(x + z)/\sqrt{2}", "y"),
        ("z-x", None, r"(x + z)/\sqrt{2}", "y"),
        ("xy", None, r"(y - x)/\sqrt{2}", "z"),
        ("yz", None, r"(z - y)/\sqrt{2}", "x"),
        # An axis in the pair is tilted into the plane
        ("xz", "x", "-y", r"(x - z)/\sqrt{2}"),
    ],
)
def test_slice_basis(name, up, across_label, up_label):
    normal, across, up_vec = utils.slice_basis(name, up)
    # A right-handed set of unit vectors, with across = up x normal as in yt
    np.testing.assert_allclose(
        np.array([across, up_vec, normal]) @ np.array([across, up_vec, normal]).T,
        np.eye(3),
        atol=1e-12,
    )
    np.testing.assert_allclose(np.cross(up_vec, normal), across)
    assert utils.direction_label(across) == across_label
    assert utils.direction_label(up_vec) == up_label


def test_up_along_an_axis_normal_is_an_error():
    with pytest.raises(ValueError, match="along the normal"):
        utils.slice_basis("x", "x")


def test_plane_window_is_where_the_plane_cuts_the_box():
    lo, hi = (0.0, 0.0, 0.0), (1.0, 2.0, 3.0)
    normal, across, up = utils.slice_basis("xz")

    # Through the middle of the box, x - z runs from -2 to 0 and y from 0 to 2
    center = np.array([0.5, 1.0, 1.5])
    (a0, a1), (u0, u1) = utils.plane_window(lo, hi, normal, center, across, up)
    np.testing.assert_allclose([a0, a1, u0, u1], [-SQRT_HALF, SQRT_HALF, -1, 1])

    # Off the middle the window is not centered: the plane x + z = 0.5 is a strip
    # from x - z = -0.5 to 0.5
    center = np.array([0.0, 0.0, 0.0]) + 0.25
    (a0, a1), (u0, u1) = utils.plane_window(lo, hi, normal, center, across, up)
    np.testing.assert_allclose([a0, a1], [-0.5 * SQRT_HALF, 0.5 * SQRT_HALF])
    np.testing.assert_allclose([u0, u1], [-0.25, 1.75])

    with pytest.raises(ValueError, match="does not cut"):
        utils.plane_window(lo, hi, normal, [5.0, 0.0, 5.0], across, up)


def test_plane_center_is_on_the_plane():
    lo, hi = (0.0, 0.0, 0.0), (1.0, 2.0, 3.0)
    normal = utils.parse_normal("xz")
    center = utils.plane_center(lo, hi, normal, 1.0)
    assert center @ normal == pytest.approx(1.0)
    # The domain center moved along the normal
    np.testing.assert_allclose(
        np.cross(center - [0.5, 1.0, 1.5], normal), 0, atol=1e-12
    )

    # The plane must reach the box: x + z runs from 0 to 4
    with pytest.raises(ValueError, match="misses the domain"):
        utils.plane_center(lo, hi, normal, 4.1 * SQRT_HALF)


def test_one_pixel_per_finest_cell_along_a_direction():
    finest = (0.25, 0.5, 0.125)
    assert utils.pixels_along((1, 0, 0), finest, 1.0) == 4
    # The smallest cell along the axes the direction runs through
    assert utils.pixels_along((SQRT_HALF, 0, SQRT_HALF), finest, 1.0) == 8
    assert utils.pixels_along((0, 1, 0), finest, 0.1) == 1
