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


def add_diff_field(ds, name, field):
    """Compute and return difference between two fields."""

    if field == "dwdz":
        # ad = ds.all_data()
        # print(ad["dwdz"].units)
        # exit()
        ds.add_field(
            name=name,
            function=_diff_dwdz,
            sampling_type="cell",
            # units="(dimensionless)",
            # units="auto",
            # dimensions=yt.units.dimensions.velocity_gradient,
        )
    else:
        sys.exit("Not supported!")


def _diff_field(field, data):
    return data[("boxlib", "vfrac")]


def _diff_dwdz(field, data):
    diff_field = np.array(data[("gas", "velocity_z_gradient_z")]) - np.array(
        data[("boxlib", "dwdz")]
    )
    diff_field /= np.array(data[("gas", "velocity_z_gradient_z")])
    return diff_field


def add_manual_gradient(ds, name):

    # ds.force_periodicity()
    ds.add_field(
        name=name,
        function=_manual_gradient,
        sampling_type="local",
        units="1/s",
        validators=[
            yt.fields.derived_field.ValidateSpatial(1, [("gas", "velocity_z")])
        ],
    )


def _manual_gradient(field, data):
    grad_field = ("gas", "velocity_z")
    assert isinstance(grad_field, tuple)
    ftype, fname = grad_field
    sl_left = slice(None, -2, None)
    sl_right = slice(2, None, None)
    div_fac = 2.0
    slice_3d = (slice(1, -1), slice(1, -1), slice(1, -1))
    axi = 2
    slice_3dl = slice_3d[:axi] + (sl_left,) + slice_3d[axi + 1 :]
    slice_3dr = slice_3d[:axi] + (sl_right,) + slice_3d[axi + 1 :]
    print(slice_3dl)
    print(slice_3dr)

    block_order = getattr(data, "_block_order", "C")
    if block_order == "F":
        print("Wtf")
        exit()
    else:
        field_data = data[grad_field]
    print(np.shape(field_data))
    dx = div_fac * data[(ftype, "dz")]

    # f = field_data[slice_3dr] / dx[slice_3d]
    # f -= field_data[slice_3dl] / dx[slice_3d]
    # print("first")
    # f = field_data[1:-1, 1:-1, 2:] / dx[1:-1, 1:-1, 1:-1]
    # print("Second")
    # f -= field_data[1:-1, 1:-1, 0:-2] / dx[1:-1, 1:-1, 1:-1]

    f = np.zeros_like(dx[1:-1, 1:-1, 1:-1], dtype=np.float64)
    imax, jmax, kmax = np.array(np.shape(dx[1:-1, 1:-1, 1:-1]))
    for k in range(kmax):
        for j in range(jmax):
            for i in range(imax):
                f[i, j, k] = (
                    0.5
                    * (field_data[i + 1, j + 1, k + 2] - field_data[i + 1, j + 1, k])
                    / dx[i + 1, j + 1, k + 1]
                )

    new_field = np.zeros_like(data[grad_field], dtype=np.float64)
    new_field = data.ds.arr(new_field, field_data.units / dx.units)

    new_field[1:-1, 1:-1, 1:-1] = f

    return new_field
    # return yt.YTArray(f, "1.0/s")

    # dxmin = data.index.get_smallest_dx()

    # gradient = np.gradient(data["velocity_z"], dxmin, axis=0, edge_order=2)
    # return yt.YTArray(gradient, "1.0/s")
