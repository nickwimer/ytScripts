"""Utility routines used throughout ytscripts."""
import fnmatch
import os

import numpy as np
import yt


def load_dataseries(datapath, pname=None, units_override=None):
    """Loads the plt files based on method."""
    if pname is not None:
        load_list = [os.path.join(datapath, x) for x in pname]
        ts = yt.DatasetSeries(load_list, units_override=units_override)
        # Find the index based on location of the selected plot files
        all_files = fnmatch.filter(sorted(os.listdir(datapath)), "plt?????")

        index_dict = {}
        for plt in pname:
            index_dict.update({plt: all_files.index(plt)})

    else:
        ts = yt.load(
            os.path.join(datapath, "plt?????"),
            units_override=units_override,
        )

        # Find the index based on location of the plot files
        all_files = fnmatch.filter(sorted(os.listdir(datapath)), "plt?????")

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
