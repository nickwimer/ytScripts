"""Utility routines used throughout ytscripts."""

import glob
import os
import re
import shutil
import sys
import tomllib

import numpy as np
import yt
from pydantic.v1.utils import deep_update


def is_notebook():
    """Check if the script is running in a Jupyter notebook."""
    return "ipykernel" in sys.modules


def is_latex_available():
    """Check if latex is available on the PATH.

    Only looks up the executable. Running a bare ``latex`` starts its interactive
    prompt and blocks waiting for input.
    """
    return shutil.which("latex") is not None


# Environment variables in which MPI launchers tell each process they start how
# many processes there are and which one it is: MPICH and Intel MPI (mpirun and
# mpiexec), Open MPI, MVAPICH, and Slurm's srun
MPI_LAUNCH_VARS = (
    ("PMI_SIZE", "PMI_RANK"),
    ("OMPI_COMM_WORLD_SIZE", "OMPI_COMM_WORLD_RANK"),
    ("MV2_COMM_WORLD_SIZE", "MV2_COMM_WORLD_RANK"),
    ("SLURM_STEP_NUM_TASKS", "SLURM_PROCID"),
)


def mpi_launch_size():
    """Return how many processes an MPI launcher started, and this one's rank.

    Reads the environment the launcher sets, without starting MPI. A plain
    ``python script.py`` run has none of it and gives (1, 0).
    """
    for size_var, rank_var in MPI_LAUNCH_VARS:
        try:
            size = int(os.environ[size_var])
        except (KeyError, ValueError):
            continue
        if size > 1:
            try:
                rank = int(os.environ.get(rank_var, 0))
            except ValueError:
                rank = 0
            return size, rank
    return 1, 0


def get_mpi_comm(no_mpi=False):
    """Return the MPI communicator if this run was launched as several processes.

    Returns None for a plain single-process run, without importing mpi4py, so
    MPI is never started and mpi4py need not be installed. Also returns None
    with no_mpi, where every process does all the work.
    """
    size, rank = mpi_launch_size()
    if size == 1:
        return None

    if no_mpi:
        if rank == 0:
            print(
                f"--no_mpi was given, so each of the {size} processes "
                "will do all the work."
            )
        return None

    try:
        from mpi4py import MPI
    except ImportError as err:
        # Stop rather than have every process repeat all the work
        if rank == 0:
            sys.exit(
                f"This run was launched as {size} MPI processes, but mpi4py "
                f"could not be loaded ({err}). Install it with "
                '"pip install mpi4py" after loading the MPI you launch with, '
                "run without mpirun or srun, or pass --no_mpi."
            )
        sys.exit(1)

    comm = MPI.COMM_WORLD
    if comm.Get_size() == 1:
        if rank == 0:
            print(
                f"Warning: this run was launched as {size} MPI processes, but "
                "MPI sees only one. mpi4py was probably built with a different "
                "MPI than the one launching it (check your loaded modules). "
                "Each process will do all the work."
            )
        return None

    return comm


def enable_parallelism(no_mpi=False):
    """Share yt's work over MPI if this run was launched as several processes.

    A plain single-process run never starts MPI. Returns True if yt runs in
    parallel.
    """
    comm = get_mpi_comm(no_mpi=no_mpi)
    if comm is None:
        return False
    return yt.enable_parallelism(communicator=comm)


class SerialComm:
    """Stand-in for an MPI communicator in a single-process run."""

    def Get_rank(self):
        return 0

    def Get_size(self):
        return 1

    def barrier(self):
        pass

    Barrier = barrier

    def gather(self, obj, root=0):
        return [obj]


def get_configs():
    """Parse the configuration options from toml file."""
    cpath = os.path.abspath(os.path.join(sys.argv[0], ".."))

    # Read the default configs
    with open(os.path.join(cpath, "config.toml"), "rb") as f:
        configs = tomllib.load(f)

    # Read any updates to the configs
    if "config_user.toml" in os.listdir(cpath):
        with open(os.path.join(cpath, "config_user.toml"), "rb") as f:
            user_configs = tomllib.load(f)

        # Update the configuration dictionary
        configs = deep_update(configs, user_configs)

    return configs


def is_plotfile(path):
    """Return True if path is an AMReX plotfile, a folder holding a Header file."""
    return os.path.isfile(os.path.join(path, "Header"))


def split_plotfile_name(name):
    """Split a plotfile name into its prefix and the number at its end.

    "pltReact01264" gives ("pltReact", 1264); a name with no number at the end
    gives (name, None).
    """
    match = re.fullmatch(r"(.*?)(\d+)", name)
    if match:
        return match.group(1), int(match.group(2))
    return name, None


def plotfile_sort_key(name):
    """Sort plotfiles by prefix, then by the number at the end of the name.

    This puts plt99999 before plt100000, which sorting by name alone does not.
    """
    prefix, number = split_plotfile_name(name)
    return (prefix, -1 if number is None else number, name)


def create_index_dict(names):
    """Number each plotfile by its place among those named the same way.

    Plotfiles that share a prefix and end in a number (plt00100, plt00200, ...) are
    numbered 0, 1, 2, ... in order of that number, so images made from them get
    consecutive frame numbers whichever of them are plotted. Names with no number at
    the end are numbered among themselves.
    """
    families = {}
    for name in sorted(names, key=plotfile_sort_key):
        prefix, number = split_plotfile_name(name)
        families.setdefault(prefix if number is not None else None, []).append(name)

    return {name: i for family in families.values() for i, name in enumerate(family)}


def find_plotfiles(datapath, pname=None, nskip=None):
    """Find the plotfiles to load and number them for output names.

    Without ``pname``, every plotfile named plt<digits> in ``datapath`` is used, so
    other plotfiles a run writes alongside (such as pltU00100 or plt00100.old.1234)
    are left out. With ``pname``, every plotfile matching those names or patterns is
    used, whatever it is called. ``nskip`` keeps every (nskip + 1)th file.

    Returns the paths to load, in order, and a dict numbering every plotfile in
    ``datapath`` (see create_index_dict).
    """
    if not datapath:
        raise ValueError("--datapath is needed: the folder that holds the plotfiles.")
    datapath = os.path.expanduser(datapath)
    if not os.path.isdir(datapath):
        raise FileNotFoundError(f"--datapath {datapath} is not a folder.")

    all_names = sorted(
        (n for n in os.listdir(datapath) if is_plotfile(os.path.join(datapath, n))),
        key=plotfile_sort_key,
    )
    step = nskip + 1 if nskip else 1

    if pname is None:
        names = [n for n in all_names if re.fullmatch(r"plt\d+", n)]
        if not names:
            message = f"No plotfiles named plt<digits> in {datapath}."
            if all_names:
                prefix, number = split_plotfile_name(all_names[0])
                hint = f"{prefix}*" if number is not None else all_names[0]
                message += (
                    f" Found {len(all_names)} other plotfiles, like {all_names[0]}:"
                    f' use them with --pname "{hint}".'
                )
            raise FileNotFoundError(message)
        names = names[::step]
    else:
        names = []
        for pattern in pname:
            if "/" in pattern or os.sep in pattern:
                raise ValueError(
                    "--pname takes plotfile names or patterns inside --datapath, not "
                    f"paths. To use the plotfiles in {pattern}, pass --datapath "
                    f"{pattern} instead."
                )
            matched = sorted(
                (
                    os.path.basename(path)
                    for path in glob.glob(os.path.join(datapath, pattern))
                    if is_plotfile(path)
                ),
                key=plotfile_sort_key,
            )
            if not matched:
                raise FileNotFoundError(
                    f'No plotfiles in {datapath} match --pname "{pattern}".'
                )
            names.extend(n for n in matched[::step] if n not in names)

    return [os.path.join(datapath, n) for n in names], create_index_dict(all_names)


def load_dataseries(datapath, pname=None, units_override=None, nprocs=1, nskip=None):
    """
    Load a series of datasets from files in a given directory.

    Parameters:
    - datapath (str): The path to the directory containing the dataset files.
    - pname (list, optional): Plotfile names or glob patterns inside datapath. When
    left out, every plotfile named plt<digits> is loaded. See find_plotfiles.
    - units_override (dict, optional): A dictionary specifying unit overrides for the
    loaded datasets. Default is None.
    - nprocs (int, optional): The number of processes to use for parallel loading.
    - nskip (int, optional): The number of files to skip between loaded datasets.

    Returns:
    - ts (yt.DatasetSeries): A series of loaded datasets.
    - index_dict (dict): Maps each plotfile name to its frame number among the
    plotfiles named the same way.
    """
    load_list, index_dict = find_plotfiles(datapath, pname=pname, nskip=nskip)

    ts = yt.DatasetSeries(
        load_list,
        units_override=units_override,
        parallel=nprocs,
    )

    return ts, index_dict


def get_attributes(ds):
    """Gets commonly used attributes from the dataset and stores in dict."""
    # Get base attributes
    ds_dict = {
        "field_list": ds.field_list,
        "derived_field_list": ds.derived_field_list,
        "time": ds.current_time,
        "dimensions": ds.domain_dimensions,
        "left_edge": ds.domain_left_edge,
        "right_edge": ds.domain_right_edge,
        "max_level": ds.max_level,
        "length_unit": ds.length_unit,
        "time_unit": ds.time_unit,
        "width": ds.domain_width,
        "center": ds.domain_center,
    }

    # Make commonly used attributes
    (dx, dy, dz) = (ds_dict["right_edge"] - ds_dict["left_edge"]) / ds_dict[
        "dimensions"
    ]
    (x_res, y_res, z_res) = ds_dict["dimensions"] * 2 ** ds_dict["max_level"]

    # Update dictionary values
    ds_dict.update(
        {
            "dxyz": (dx, dy, dz),
            "resolution": (x_res, y_res, z_res),
        }
    )
    return ds_dict


AXIS_VECTORS = {
    "x": np.array([1.0, 0.0, 0.0]),
    "y": np.array([0.0, 1.0, 0.0]),
    "z": np.array([0.0, 0.0, 1.0]),
}

# One axis (x), an axis pair (xz, or x+z) or a signed pair (x-z)
NORMAL_PATTERN = re.compile(r"([xyz])(?:([+-]?)([xyz]))?")

NORMAL_FORMS = (
    "x, y or z, a pair of different axes such as xz (normal (1, 0, 1)), "
    "or a signed pair such as x-z (normal (1, 0, -1))"
)


def _match_normal(name):
    """Return the regex match for a --normal value, or raise ValueError."""
    match = NORMAL_PATTERN.fullmatch(name) if isinstance(name, str) else None
    if match is None or match[1] == match[3]:
        raise ValueError(f"The normal must be {NORMAL_FORMS}, not {name!r}")
    return match


def canonical_normal(name):
    """Return a --normal value in its standard form: x+z becomes xz."""
    match = _match_normal(name)
    if match[3] is None:
        return match[1]
    return f"""{match[1]}{"-" if match[2] == "-" else ""}{match[3]}"""


def parse_normal(name):
    """Return the unit normal vector named by a --normal value."""
    match = _match_normal(name)
    normal = AXIS_VECTORS[match[1]].copy()
    if match[3] is not None:
        sign = -1.0 if match[2] == "-" else 1.0
        normal += sign * AXIS_VECTORS[match[3]]
    return normal / np.linalg.norm(normal)


def is_axis_normal(name):
    """Return whether a --normal value is one of the coordinate axes."""
    return canonical_normal(name) in AXIS_VECTORS


def default_up(name):
    """Return the axis drawn up a slice image by default.

    z for normal x and y, y for normal z, and the axis left out of a pair, so y for
    xz and x-z.
    """
    name = canonical_normal(name)
    if name in AXIS_VECTORS:
        return {"x": "z", "y": "z", "z": "y"}[name]
    return next(axis for axis in "xyz" if axis not in name)


def slice_basis(name, up=None):
    """Return the unit normal and the unit vectors across and up a slice image.

    ``up`` names the axis to draw up the image (default from default_up()). An
    axis that is not in the plane is tilted into it, so for normal xz, up x points
    along (x - z)/sqrt(2). Across is up x normal, as in yt's off-axis slices, so
    across, up and the normal form a right-handed set.
    """
    normal = parse_normal(name)
    if up is None:
        up = default_up(name)
    if up not in AXIS_VECTORS:
        raise ValueError(f"Up must be x, y or z, not {up!r}")
    up_vec = AXIS_VECTORS[up] - np.dot(AXIS_VECTORS[up], normal) * normal
    if np.linalg.norm(up_vec) < 1e-8:
        raise ValueError(f"Up {up} points along the normal {name}")
    up_vec /= np.linalg.norm(up_vec)
    across = np.cross(up_vec, normal)
    return normal, across, up_vec


def direction_label(vector):
    """Return a math-text label for a direction, such as (x - z)/\\sqrt{2}."""
    vector = np.asarray(vector, dtype=np.float64)
    terms = [(axis, value) for axis, value in zip("xyz", vector) if abs(value) > 1e-8]
    if len(terms) == 1:
        axis, value = terms[0]
        return axis if value > 0 else f"-{axis}"

    magnitudes = np.array([abs(value) for _, value in terms])
    equal = np.allclose(magnitudes, magnitudes[0])
    prefix = ""
    if equal:
        if all(value < 0 for _, value in terms):
            # -(x + z) reads better than (-x - z)
            prefix = "-"
            terms = [(axis, -value) for axis, value in terms]
        else:
            # Lead with a positive term: (z - y) rather than (-y + z)
            terms.sort(key=lambda term: term[1] < 0)
    label = ""
    for i, (axis, value) in enumerate(terms):
        coeff = "" if equal else f"{abs(value):.3g}"
        if i == 0:
            label += f"""{"-" if value < 0 else ""}{coeff}{axis}"""
        else:
            label += f""" {"-" if value < 0 else "+"} {coeff}{axis}"""
    if equal:
        scale = 1.0 / magnitudes[0] ** 2
        root = f"{scale:.0f}" if np.isclose(scale, round(scale)) else f"{scale:.3g}"
        return rf"{prefix}({label})/\sqrt{{{root}}}"
    return label


def code_length_values(ds, value):
    """Return a position or length as plain floats in code_length."""
    if hasattr(value, "units"):
        return np.asarray(
            ds.arr(np.asarray(value.d), str(value.units)).to("code_length").d,
            dtype=np.float64,
        )
    return np.asarray(value, dtype=np.float64)


def box_corners(left_edge, right_edge):
    """Return the 8 corners of a box as an (8, 3) array."""
    lo = np.asarray(left_edge, dtype=np.float64)
    hi = np.asarray(right_edge, dtype=np.float64)
    return np.array(
        [
            [(lo, hi)[i][0], (lo, hi)[j][1], (lo, hi)[k][2]]
            for i in (0, 1)
            for j in (0, 1)
            for k in (0, 1)
        ]
    )


def plane_box_points(left_edge, right_edge, normal, point):
    """Return the corners of the polygon where a plane cuts a box.

    The plane holds ``point`` and has the unit ``normal``. Raises ValueError if it
    misses the box.
    """
    normal = np.asarray(normal, dtype=np.float64)
    corners = box_corners(left_edge, right_edge)
    dist = corners @ normal - np.dot(np.asarray(point, dtype=np.float64), normal)
    tol = 1e-12 * max(1.0, np.abs(corners).max())

    points = [corner for corner, d in zip(corners, dist) if abs(d) <= tol]
    # The edges of the box join corners that differ in one coordinate
    for a in range(8):
        for b in range(a + 1, 8):
            if bin(a ^ b).count("1") != 1:
                continue
            if (dist[a] < -tol and dist[b] > tol) or (dist[a] > tol and dist[b] < -tol):
                frac = dist[a] / (dist[a] - dist[b])
                points.append(corners[a] + frac * (corners[b] - corners[a]))
    if not points:
        raise ValueError("The slice plane does not cut the domain")
    return np.array(points)


def plane_window(left_edge, right_edge, normal, center, across, up):
    """Return the part of a slice plane inside the domain, around its center.

    The plane goes through ``center`` with the unit ``normal``. Returns
    ((across_min, across_max), (up_min, up_max)), as offsets from ``center`` along
    the unit vectors ``across`` and ``up``.
    """
    center = np.asarray(center, dtype=np.float64)
    offsets = plane_box_points(left_edge, right_edge, normal, center) - center
    along_across = offsets @ np.asarray(across, dtype=np.float64)
    along_up = offsets @ np.asarray(up, dtype=np.float64)
    return (
        (along_across.min(), along_across.max()),
        (along_up.min(), along_up.max()),
    )


def plane_center(left_edge, right_edge, normal, distance):
    """Return the point of the plane normal . r = distance nearest the domain center.

    Raises ValueError if the plane misses the domain.
    """
    lo = np.asarray(left_edge, dtype=np.float64)
    hi = np.asarray(right_edge, dtype=np.float64)
    normal = np.asarray(normal, dtype=np.float64)
    reach = box_corners(lo, hi) @ normal
    if not reach.min() <= distance <= reach.max():
        raise ValueError(
            f"The plane at distance {distance} along the normal misses the domain, "
            f"which spans {reach.min():.6g} to {reach.max():.6g}"
        )
    domain_center = (lo + hi) / 2.0
    return domain_center + (distance - np.dot(domain_center, normal)) * normal


def pixels_along(direction, finest_dxyz, length):
    """Return how many pixels give one per finest cell over a length along a direction.

    The pixel is the size of the smallest finest cell along the axes the direction
    has a part along.
    """
    direction = np.asarray(direction, dtype=np.float64)
    sizes = [float(dx) for dx, part in zip(finest_dxyz, direction) if abs(part) > 1e-8]
    return max(1, int(np.ceil(length / min(sizes) - 1e-6)))


def get_fig_aspect_ratio(xlen, ylen, base=5):
    """Get the aspect ratio to fit the data."""

    aspect_ratio = np.ceil(ylen / xlen)
    fx = base * (0.5 + aspect_ratio)
    fy = base

    return fx, fy


def _velocity_x(field, data):
    return yt.YTArray(data["velocityx"], "m/s")


def _velocity_y(field, data):
    return yt.YTArray(data["velocityy"], "m/s")


def _velocity_z(field, data):
    return yt.YTArray(data["velocityz"], "m/s")


def define_velocity_fields(ds):
    """Add some velocity fields."""
    ds.add_field(
        name=("boxlib", "velocity_x"),
        function=_velocity_x,
        sampling_type="cell",
        units="m/s",
        display_name="u",
    )
    ds.add_field(
        name=("boxlib", "velocity_y"),
        function=_velocity_y,
        sampling_type="cell",
        units="m/s",
        display_name="v",
    )
    ds.add_field(
        name=("boxlib", "velocity_z"),
        function=_velocity_z,
        sampling_type="cell",
        units="m/s",
        display_name="w",
    )


def get_gradient_field(ds, field, grad_type):
    """Add the gradient field and return new field name."""
    ds.force_periodicity()
    ds.add_gradient_fields(field)

    return f"{field}_gradient_{grad_type}"


def compute_elem_mass_fraction(attributes, keys=None):
    """Compute the elem mass fraction for streams."""

    # define atomic masses dict
    atomic_masses = {"C": 12.01, "H": 1.00, "O": 16.00, "N": 14.01}

    spec_dict = {}
    fields = []
    # loop over all fields
    for fname in attributes["field_list"]:
        # Only look at species (contain Y)
        if "Y(" in fname[1]:
            cut_name = fname[1][2:-1]
            if cut_name[0:2] == "NC":
                cut_name = cut_name[1:]

            elem_dict = re.findall(r"([A-Z][a-z]?)(\d*)", cut_name)

            if keys and cut_name in keys:
                fields.append(fname)

                # add entry to the species dict
                spec_dict[cut_name] = {"C": 0, "H": 0, "O": 0, "N": 0}

                # print(elem_dict{"C"})
                for elem in elem_dict:
                    if elem[1] == "":
                        num = 1
                    else:
                        num = int(elem[1])

                    if elem[0] == "C":
                        spec_dict[cut_name]["C"] += num
                    elif elem[0] == "H":
                        spec_dict[cut_name]["H"] += num
                    elif elem[0] == "O":
                        spec_dict[cut_name]["O"] += num
                    elif elem[0] == "N":
                        spec_dict[cut_name]["N"] += num

            elif not keys:
                fields.append(fname)

                # add entry to the species dict
                spec_dict[cut_name] = {"C": 0, "H": 0, "O": 0, "N": 0}

                # print(elem_dict{"C"})
                for elem in elem_dict:
                    if elem[1] == "":
                        num = 1
                    else:
                        num = int(elem[1])

                    if elem[0] == "C":
                        spec_dict[cut_name]["C"] += num
                    elif elem[0] == "H":
                        spec_dict[cut_name]["H"] += num
                    elif elem[0] == "O":
                        spec_dict[cut_name]["O"] += num
                    elif elem[0] == "N":
                        spec_dict[cut_name]["N"] += num

    # Mass of each element in each species, as a fraction of the species' mass
    elem_mass_frac_dict = {}
    for spec, counts in spec_dict.items():
        masses = {elem: counts[elem] * mass for elem, mass in atomic_masses.items()}
        total_mass = sum(masses.values())
        # A species with none of these elements (e.g. AR) has no fractions to give
        elem_mass_frac_dict[spec] = {
            elem: (mass / total_mass if total_mass else 0.0)
            for elem, mass in masses.items()
        }

    return elem_mass_frac_dict, atomic_masses, fields
