"""Tests for helpers in ytscripts.utilities."""

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
