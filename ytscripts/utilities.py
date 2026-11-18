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
