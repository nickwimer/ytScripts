"""Tests for starting MPI only when a run was launched as several processes."""

import os
import shutil
import subprocess
import sys

import pytest

import ytscripts.utilities as utils

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def plain_env(monkeypatch):
    """Remove every MPI launcher variable, as in a plain python run."""
    for size_var, rank_var in utils.MPI_LAUNCH_VARS:
        monkeypatch.delenv(size_var, raising=False)
        monkeypatch.delenv(rank_var, raising=False)
    return monkeypatch


def clean_environ():
    """Return a copy of the environment without MPI launcher variables."""
    env = dict(os.environ)
    for size_var, rank_var in utils.MPI_LAUNCH_VARS:
        env.pop(size_var, None)
        env.pop(rank_var, None)
    return env


def test_launch_size_from_environment(plain_env):
    assert utils.mpi_launch_size() == (1, 0)

    plain_env.setenv("PMI_SIZE", "4")
    plain_env.setenv("PMI_RANK", "2")
    assert utils.mpi_launch_size() == (4, 2)

    # One process is not a parallel launch
    plain_env.setenv("PMI_SIZE", "1")
    assert utils.mpi_launch_size() == (1, 0)

    # Slurm's srun, with no rank variable
    plain_env.setenv("SLURM_STEP_NUM_TASKS", "8")
    assert utils.mpi_launch_size() == (8, 0)

    plain_env.setenv("SLURM_STEP_NUM_TASKS", "not a number")
    assert utils.mpi_launch_size() == (1, 0)


def test_plain_run_never_loads_mpi4py():
    """Without a launcher, mpi4py is not imported, so MPI never starts."""
    code = (
        "import sys; import ytscripts.utilities as u; "
        "print(u.enable_parallelism(), 'mpi4py' in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO,
        env=clean_environ(),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["False", "False"]
    assert "Could not enable parallelism" not in result.stderr


def test_no_mpi_skips_mpi_under_a_launch(plain_env, capsys):
    plain_env.setenv("PMI_SIZE", "2")
    plain_env.setenv("PMI_RANK", "0")
    # Any import of mpi4py would now fail
    plain_env.setitem(sys.modules, "mpi4py", None)

    assert utils.get_mpi_comm(no_mpi=True) is None
    assert "each of the 2 processes" in capsys.readouterr().out


def test_launched_run_without_mpi4py_stops(plain_env):
    plain_env.setenv("PMI_SIZE", "2")
    plain_env.setitem(sys.modules, "mpi4py", None)

    plain_env.setenv("PMI_RANK", "0")
    with pytest.raises(SystemExit) as stop:
        utils.get_mpi_comm()
    assert "launched as 2 MPI processes" in str(stop.value.code)
    assert "--no_mpi" in str(stop.value.code)

    # Only the first process explains
    plain_env.setenv("PMI_RANK", "1")
    with pytest.raises(SystemExit) as stop:
        utils.get_mpi_comm()
    assert stop.value.code == 1


def test_serial_comm_acts_as_one_process():
    comm = utils.SerialComm()
    assert comm.Get_rank() == 0
    assert comm.Get_size() == 1
    comm.barrier()
    comm.Barrier()
    assert comm.gather("data", root=0) == ["data"]


def mpi_available():
    if shutil.which("mpirun") is None:
        return False
    try:
        import mpi4py  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(not mpi_available(), reason="needs mpirun and mpi4py")
def test_mpirun_shares_the_work():
    code = (
        "import ytscripts.utilities as u; c = u.get_mpi_comm(); "
        "print(c.Get_rank(), c.Get_size())"
    )
    result = subprocess.run(
        ["mpirun", "-np", "2", sys.executable, "-c", code],
        cwd=REPO,
        env=clean_environ(),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert sorted(result.stdout.splitlines()) == ["0 2", "1 2"]
