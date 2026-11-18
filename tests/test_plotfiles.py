"""Tests for finding plotfiles by name."""

import os

import pytest

import ytscripts.utilities as utils
import ytscripts.ytargs as ytargs


def make_plotfiles(folder, *names):
    """Make empty AMReX-style plotfile folders, each holding a Header file."""
    for name in names:
        (folder / name).mkdir()
        (folder / name / "Header").write_text("HyperCLaw-V1.1\n")


def names(paths):
    """Return the file names of a list of paths."""
    return [os.path.basename(path) for path in paths]


def test_default_takes_plt_digits_in_number_order(tmp_path):
    make_plotfiles(
        tmp_path,
        "plt100000",
        "plt00200",
        "plt99999",
        "plt00100",
        "pltU00100",
        "plt00100.old.4821",
        "pltReact01264",
    )
    (tmp_path / "plt_notes.txt").write_text("not a plotfile")
    (tmp_path / "plt00300").mkdir()  # no Header yet: still being written

    paths, index = utils.find_plotfiles(str(tmp_path))
    assert names(paths) == ["plt00100", "plt00200", "plt99999", "plt100000"]
    assert [index[name] for name in names(paths)] == [0, 1, 2, 3]
    # Other families are numbered on their own
    assert index["pltU00100"] == 0
    assert index["pltReact01264"] == 0


def test_pname_takes_any_name(tmp_path):
    make_plotfiles(
        tmp_path,
        "pltReact01264",
        "pltReact00500",
        "pltReact10000",
        "plt00100",
        "final_state",
    )
    paths, index = utils.find_plotfiles(str(tmp_path), pname=["pltReact*"])
    assert names(paths) == ["pltReact00500", "pltReact01264", "pltReact10000"]
    assert [index[name] for name in names(paths)] == [0, 1, 2]

    # One file keeps its frame number among the files named like it
    paths, index = utils.find_plotfiles(str(tmp_path), pname=["pltReact01264"])
    assert names(paths) == ["pltReact01264"]
    assert index["pltReact01264"] == 1

    # A name with no number works too
    paths, _ = utils.find_plotfiles(str(tmp_path), pname=["final_state"])
    assert names(paths) == ["final_state"]


def test_pname_patterns_keep_their_order_without_repeats(tmp_path):
    make_plotfiles(tmp_path, "plt00100", "plt00200", "plt00300")
    paths, _ = utils.find_plotfiles(str(tmp_path), pname=["plt00300", "plt00*"])
    assert names(paths) == ["plt00300", "plt00100", "plt00200"]


def test_nskip(tmp_path):
    make_plotfiles(tmp_path, *[f"plt{step:05d}" for step in range(0, 700, 100)])
    paths, _ = utils.find_plotfiles(str(tmp_path), nskip=2)
    assert names(paths) == ["plt00000", "plt00300", "plt00600"]


def test_no_plt_files_suggests_pname(tmp_path):
    make_plotfiles(tmp_path, "pltReact01264", "pltReact00500")
    with pytest.raises(FileNotFoundError, match=r'use them with --pname "pltReact\*"'):
        utils.find_plotfiles(str(tmp_path))


def test_pname_with_a_path_suggests_datapath(tmp_path):
    with pytest.raises(ValueError, match="pass --datapath ../runs/ instead"):
        utils.find_plotfiles(str(tmp_path), pname=["../runs/"])


def test_unmatched_pname_and_missing_folder(tmp_path):
    make_plotfiles(tmp_path, "plt00100")
    with pytest.raises(FileNotFoundError, match='match --pname "pltReact'):
        utils.find_plotfiles(str(tmp_path), pname=["pltReact*"])
    with pytest.raises(FileNotFoundError, match="is not a folder"):
        utils.find_plotfiles(str(tmp_path / "missing"))


def test_datapath_is_required_with_a_hint(capsys):
    parser = ytargs.ytVisArgs()
    with pytest.raises(SystemExit):
        parser.get_args(["--pname", "../Below_Flame_Holder_PP/", "--field", "T"])
    err = capsys.readouterr().err
    assert "--datapath" in err
    assert "the folder goes after --datapath" in err
