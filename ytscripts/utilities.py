"""Utility routines used throughout ytscripts."""
import copy
import glob
import os
import re
import sys

import numpy as np
import yt


def get_files(datapath, pattern="plt*"):
    return sorted(
        [os.path.basename(x) for x in glob.glob(os.path.join(datapath, pattern))]
    )


def load_dataseries(datapath, pname=None, units_override=None, nprocs=1, nskip=None):
    """Loads the plt files based on method."""
    if pname is not None:
        if "?" in pname[0] and len(pname) == 1:
            if nskip:
                select_files = get_files(datapath, pname[0])
                load_files = select_files[0 : len(select_files) : nskip + 1]
                load_list = [os.path.join(datapath, x) for x in load_files]
                print(load_list)
                # exit()
                ts = yt.DatasetSeries(
                    load_list,
                    units_override=units_override,
                    parallel=nprocs,
                )

                # Find the index based on location of the plot files
                all_files = get_files(datapath)

                index_dict = {}
                for plt in all_files:
                    index_dict.update({plt: all_files.index(plt)})
            else:
                ts = yt.load(
                    os.path.join(datapath, pname[0]),
                    units_override=units_override,
                    parallel=nprocs,
                )

                # Find the index based on location of the plot files
                all_files = get_files(datpath, pname[0])

                index_dict = {}
                for plt in all_files:
                    index_dict.update({plt: all_files.index(plt)})

        elif "?" in pname[0] and len(pname) > 1:
            sys.exit("multiple ? character inputs not supported yet.")
        else:
            load_list = [os.path.join(datapath, x) for x in pname]
            ts = yt.DatasetSeries(
                load_list, units_override=units_override, parallel=nprocs
            )

            # Find the index based on location of the selected plot files
            all_files = get_files(datapath)

            index_dict = {}
            for plt in pname:
                index_dict.update({plt: all_files.index(plt)})

    else:
        if nskip:
            select_files = get_files(datapath)
            load_files = select_files[0 : len(select_files) : nskip + 1]
            load_list = [os.path.join(datapath, x) for x in load_files]

            ts = yt.DatasetSeries(
                load_list,
                units_override=units_override,
                parallel=nprocs,
            )

            # Find the index based on location of the plot files
            all_files = get_files(datapath)

            index_dict = {}
            for plt in all_files:
                index_dict.update({plt: all_files.index(plt)})

        else:
            ts = yt.load(
                os.path.join(datapath, "plt?????"),
                units_override=units_override,
                parallel=nprocs,
            )

            # Find the index based on location of the plot files
            all_files = get_files(datapath)

            index_dict = {}
            for plt in all_files:
                index_dict.update({plt: all_files.index(plt)})

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

    # Compute the elemental mass fraction from the spec_dict
    # elem_mass_frac_dict = {"C": 0, "H": 0, "O": 0, "N": 0}
    elem_mass_frac_dict = copy.deepcopy(spec_dict)
    for spec in spec_dict:
        elem_mass_frac_dict[spec]["C"] += spec_dict[spec]["C"] * atomic_masses["C"]
        elem_mass_frac_dict[spec]["H"] += spec_dict[spec]["H"] * atomic_masses["H"]
        elem_mass_frac_dict[spec]["O"] += spec_dict[spec]["O"] * atomic_masses["O"]
        elem_mass_frac_dict[spec]["N"] += spec_dict[spec]["N"] * atomic_masses["N"]

    for spec in elem_mass_frac_dict:
        total_mass = (
            elem_mass_frac_dict[spec]["C"]
            + elem_mass_frac_dict[spec]["H"]
            + elem_mass_frac_dict[spec]["O"]
            + elem_mass_frac_dict[spec]["N"]
        )
        elem_mass_frac_dict[spec]["C"] /= total_mass
        elem_mass_frac_dict[spec]["H"] /= total_mass
        elem_mass_frac_dict[spec]["O"] /= total_mass
        elem_mass_frac_dict[spec]["N"] /= total_mass

    return elem_mass_frac_dict, atomic_masses, fields
