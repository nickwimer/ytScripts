"""2D slice down the middle of the domain."""

import importlib
import os
import pickle as pl
import sys
from inspect import getmembers, isfunction

import numpy as np
import yt
from skimage.measure import find_contours
from yt.units.yt_array import YTArray

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import matplotlib.pyplot as plt  # noqa: E402

import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402


def configure_tex(use_tex):
    """Render plot text with LaTeX, only when asked for and LaTeX is installed.

    LaTeX rendering is opt-in: it is slower, and a broken TeX install can make
    matplotlib wait forever on its luatex helper. Returns whether it is on.
    """
    if not use_tex:
        return False
    if not utils.is_latex_available():
        print("--use_tex was given but LaTeX was not found; using standard fonts.")
        return False
    plt.rc("text", usetex=True)
    return True


def get_parser():
    """Get the parser."""
    ytparse = ytargs.ytVisArgs()
    # Add in the arguments needed for SlicePlot
    ytparse.orientation_args(up=True)
    ytparse.vis_2d_args()
    ytparse.slice_args()

    return ytparse


def get_base_parser():
    """Get the base level parser primarily for documentation."""
    return get_parser().get_parser()


def get_args(parser):
    """Get the arguments from the parser."""
    # Parse the command line, merged with the input file if one is given
    args = parser.get_args()

    # Return the parsed arguments as a dict
    return args


def image_axes(normal, up=None):
    """Return the axes drawn across and up the slice image, and whether yt swaps them.

    yt draws (y, z) for normal x, (z, x) for normal y and (x, y) for normal z, and
    its swap_axes() exchanges the two. ``up`` names the axis to draw up the image.
    Without it, this script keeps yt's choice, except that it swaps the axes for
    normal y so that z points up there too.
    """
    yt_axes = {"x": ("y", "z"), "y": ("z", "x"), "z": ("x", "y")}
    if normal not in yt_axes:
        raise ValueError(f"The normal must be x, y or z, not {normal!r}")
    horizontal, vertical = yt_axes[normal]
    if up is None:
        swap = normal == "y"
    elif up in (horizontal, vertical):
        swap = up == horizontal
    else:
        raise ValueError(
            f"Up must be {horizontal} or {vertical} for normal {normal}, not {up!r}"
        )
    if swap:
        horizontal, vertical = vertical, horizontal
    return horizontal, vertical, swap


def contour_lines(image, level, extent):
    """Return the contour lines of an image in plot coordinates.

    ``image`` is indexed [row, column] with row 0 at the bottom, and ``extent`` is
    (left, right, bottom, top) of the whole image, as matplotlib's imshow uses. Each
    line is an (N, 2) array of horizontal and vertical positions, measured from the
    pixel centers.
    """
    image = np.asarray(image, dtype=np.float64)
    nrows, ncols = image.shape
    left, right, bottom, top = extent
    dh = (right - left) / ncols
    dv = (top - bottom) / nrows

    return [
        np.column_stack(
            (left + (line[:, 1] + 0.5) * dh, bottom + (line[:, 0] + 0.5) * dv)
        )
        for line in find_contours(image, level=float(level))
    ]


def create_slice_plot(
    ds,
    args,
    configs,
    slc_center=None,
    vis_field=None,
    axes_unit=None,
    pbox_width=None,
    pbox_center=None,
    index=None,
    udf_funcs=None,
    eb_var_name=None,
):
    # Get updated attributes for each plt file
    ds_attributes = utils.get_attributes(ds=ds)

    # get number of cells in the level 0 non-EB grid
    if args["grid_info"]:
        dx0, dy0, dz0 = np.array(ds_attributes["dxyz"])
        if ("boxlib", eb_var_name) in ds.field_list:
            data = ds.covering_grid(
                level=0,
                left_edge=ds_attributes["left_edge"],
                dims=ds_attributes["dimensions"],
                ds=ds,
            )
            num_cells_0 = float(data[("boxlib", eb_var_name)].sum())
        else:
            # No EB in this dataset, so every level 0 cell is fluid
            num_cells_0 = float(np.prod(ds_attributes["dimensions"]))
        domain_volume = dx0 * dy0 * dz0 * num_cells_0

    # The axes drawn across and up the image
    horizontal, vertical, swap = image_axes(args["normal"], args["up"])

    # Image resolution: one pixel per finest cell, unless --buff gives it
    if args["buff"] is not None:
        buff_size = tuple(args["buff"])
    else:
        resolution = dict(zip("xyz", ds_attributes["resolution"]))
        buff_size = (resolution[horizontal], resolution[vertical])
    # yt 4.3 draws only part of the image when it swaps the axes of a buffer that is
    # not square
    if swap:
        buff_size = (max(buff_size),) * 2

    # Plot the field
    slc = yt.SlicePlot(
        ds=ds,
        normal=args["normal"],
        fields=vis_field,
        center=slc_center,
        buff_size=buff_size,
    )
    if swap:
        slc.swap_axes()
    slc.set_axes_unit(axes_unit)
    slc.set_origin("native")

    if args["pbox"] is not None:
        # --pbox is given across then up the image, but yt sets the window in its
        # own order, from before the swap
        if swap:
            pbox_width, pbox_center = pbox_width[::-1], pbox_center[::-1]
        slc.set_width(pbox_width)
        slc.set_center(pbox_center)
    if args["fbounds"] is not None:
        slc.set_zlim(vis_field, args["fbounds"][0], args["fbounds"][1])
    if not args["no_time"]:
        slc.annotate_timestamp(draw_inset_box=True)
    if args["grids"]:
        if len(args["grids"]) > 0:
            slc.annotate_grids(
                alpha=args["grids"][0],
                min_level=args["grids"][1],
                max_level=args["grids"][2],
                linewidth=args["grids"][3],
            )
        else:
            slc.annotate_grids()

    # annotate the cell edges of the mesh
    if args["cells"]:
        slc.annotate_cell_edges(
            line_width=float(args["cells"][0]),
            alpha=float(args["cells"][1]),
            color=args["cells"][2],
        )
    print(f"""Plotting {vis_field} for index {index}...""")
    slc.set_log(vis_field, args["plot_log"])
    slc.set_cmap(field=vis_field, cmap=args["cmap"])

    # Set the colorbar label for gradient fields (too long)
    if args["gradient"]:
        if args["gradient"] == "magnitude":
            new_label = rf"""|$\nabla$ {args["field"]}|"""
        else:
            new_label = rf"""$\nabla_{args["gradient"]}$ {args["field"]}"""

        slc.set_colorbar_label(field=vis_field, label=new_label)

    # Remove the units
    if args["no_units"]:
        slc.set_colorbar_label(
            field=vis_field,
            label=(
                configs["vis_field_attrs"][vis_field]["label"]
                if vis_field in configs["vis_field_attrs"]
                else vis_field
            ),
        )
        # yt labels its own axes from before the swap, then swaps the labels too
        xlabel, ylabel = (vertical, horizontal) if swap else (horizontal, vertical)
        slc.set_xlabel(f"${xlabel}$")
        slc.set_ylabel(f"${ylabel}$")

    # Override the colorbar label
    if vis_field in configs["vis_field_attrs"] and not args["no_units"]:
        slc.set_colorbar_label(
            field=vis_field,
            label=configs["vis_field_attrs"][vis_field]["label"],
        )

    # Remove the colorbar label if plotting on top
    if configs["cbar_attrs"]["label"]["loc"] == "top":
        slc.set_colorbar_label(field=vis_field, label="")

    slc.set_font_size(configs["plot_attrs"]["base"]["fontsize"])

    # Convert the slice to matplotlib figure
    fig = slc.export_to_mpl_figure(
        nrows_ncols=(1, 1),
        cbar_pad=configs["cbar_attrs"]["base"]["pad"],
        cbar_location=configs["cbar_attrs"]["base"]["loc"],
    )

    # Get the axes from the figure handle
    ax = fig.axes[0]

    axlabel_size = configs["plot_attrs"]["axes"]["labelsize"]
    ax.tick_params(axis="x", labelsize=axlabel_size)
    ax.tick_params(axis="y", labelsize=axlabel_size)

    axc = fig.axes[1]
    axc.tick_params(axis="x", labelsize=axlabel_size)
    axc.tick_params(axis="y", labelsize=axlabel_size)

    if configs["cbar_attrs"]["label"]["loc"] == "top":
        axc.set_title(
            (
                configs["vis_field_attrs"][vis_field]["label"]
                if vis_field in configs["vis_field_attrs"]
                else vis_field
            ),
            fontsize=configs["cbar_attrs"]["base"]["fontsize"],
            pad=configs["cbar_attrs"]["title"]["pad"],
        )
    axc.set_xlabel("")

    # The slice image as drawn: its extent covers whatever region --center, --pbox
    # and --buff selected, in the axes units. Contours and the EB cover go on it.
    extent = ax.get_images()[0].get_extent()

    if args["contour"] is not None:
        # contour must be a multiple of three arguments
        if not len(args["contour"]) % 3 == 0:
            sys.exit(
                "Contour argument must be a multiple of 3! [FIELD, VALUE, COLOR] "
                f"but got {args['contour']}"
            )
        else:
            num_contours = len(args["contour"]) // 3

        # Compute and plot the contours
        for icnt in range(num_contours):
            if args["clw"] is None:
                linewidth = 1.0
            else:
                linewidth = args["clw"][icnt]

            idx = icnt * 3
            image = np.asarray(slc.frb[args["contour"][idx]])
            # The buffer keeps yt's own axes; the plot transposes it when they are
            # swapped
            if swap:
                image = image.T

            for line in contour_lines(image, args["contour"][idx + 1], extent):
                ax.plot(
                    line[:, 0],
                    line[:, 1],
                    alpha=1.0,
                    color=args["contour"][idx + 2],
                    zorder=10,
                    linewidth=linewidth,
                )

    # Add grid information to the slice plot
    if args["grid_info"]:
        dx0, dy0, dz0 = np.array(ds_attributes["dxyz"])

        level_data = ds.index.level_stats[0 : ds.index.max_level + 1]

        total_cells = 0
        cell_vol_percents = np.zeros(np.shape(level_data))
        for ilev, lev in enumerate(level_data):
            dx = dx0 / (2**ilev)
            dy = dy0 / (2**ilev)
            dz = dz0 / (2**ilev)
            total_cells += lev[1]
            cell_vol_percents[ilev] = np.minimum(
                lev[1] * dx * dy * dz / domain_volume * 100, 100
            )

        # Define text with grid info (LaTeX treats a bare % as a comment)
        pct = r"\%" if plt.rcParams["text.usetex"] else "%"
        text_string = ""
        for ilev in np.arange(args["grid_info"][2], args["grid_info"][3] + 1):
            text_string += (
                f"Level {int(ilev)} vol: {cell_vol_percents[int(ilev)]:.1f}{pct}\n"
            )
        text_string += f"{total_cells * 3 / 1e6:.0f}M  DOF"

        # Add text
        ax.text(
            x=args["grid_info"][0],
            y=args["grid_info"][1],
            s=text_string,
            color="white",
            bbox=dict(facecolor="black", edgecolor="white", boxstyle="round"),
        )

    # Remove the EB boundary defined by vfrac < 0.5 (rm_eb is the fill color, and
    # 0 is a valid choice)
    if args["rm_eb"] is not None:
        if udf_funcs and "rm_eb" in udf_funcs:
            ax = udf_funcs["rm_eb"](ax)
        else:
            vfrac = slc.frb[("boxlib", eb_var_name)].to_ndarray()
            # Lay the cover out like the slice image
            if swap:
                vfrac = vfrac.T
            m_vfrac = np.ma.array(
                args["rm_eb"] * np.ones(np.shape(vfrac)),
                mask=(vfrac > 0.5),
                fill_value=np.nan,
            )
            ax.imshow(
                m_vfrac,
                origin="lower",
                extent=extent,
                aspect="equal",
                cmap="binary",
                vmin=0.0,
                vmax=1.0,
            )

    fig.tight_layout()
    return fig


def main():
    # Parse the input arguments
    parser = get_parser()
    args = get_args(parser)

    # Parse the configuration options
    configs = utils.get_configs()

    # Import UDFs
    udf_funcs = {}
    if args["add_udf"]:
        udf_path = os.path.abspath(os.path.join(sys.argv[0], "../../", "udfs"))
        sys.path.append(udf_path)
        udf_mod = importlib.import_module("udfs" + f""".{args["add_udf"][:-3]}""")

        udf_tups = getmembers(udf_mod, isfunction)

        # Convert the tuples to dict
        for iname, ifunc in udf_tups:
            udf_funcs.update({iname: ifunc})

    # Render text with LaTeX only when asked for
    configure_tex(args["use_tex"])

    # Make the output directory for images
    if args["outpath"]:
        imgpath = args["outpath"]
    else:
        imgpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata/", "images"))
    os.makedirs(imgpath, exist_ok=True)

    # Override the units if needed
    if args["SI"]:
        units_override = {
            "length_unit": (1.0, "m"),
            "time_unit": (1.0, "s"),
            "mass_unit": (1.0, "kg"),
            "velocity_unit": (1.0, "m/s"),
        }
        axes_unit = "m"
        eb_var_name = "volFrac"
    else:
        units_override = None
        axes_unit = "cm"
        eb_var_name = "vfrac"

    # Load data files into dataset series
    ts, index_dict = utils.load_dataseries(
        datapath=args["datapath"],
        pname=args["pname"],
        units_override=units_override,
        nskip=args["nskip"],
    )

    # Get base attributes
    base_attributes = utils.get_attributes(ds=ts[0])

    if args["verbose"]:
        print(f"""The fields in this dataset are: {base_attributes["field_list"]}""")
        print(
            f"""The derived fields in this dataset are: """
            f"""{base_attributes["derived_field_list"]}"""
        )

    # Set the center of the plot for loading the data
    if args["center"] is not None:
        slc_center = args["center"]
    else:
        # Set the center based on the plt data
        slc_center = (
            base_attributes["right_edge"] + base_attributes["left_edge"]
        ) / 2.0
        # provide slight offset to avoid grid alignment vis issues
        slc_center += YTArray(args["grid_offset"], base_attributes["length_unit"])

    # Compute the center of the image for plotting
    if args["pbox"]:
        # Set the center based on the pbox
        pbox_center = [
            (args["pbox"][2] + args["pbox"][0]) / 2.0,
            (args["pbox"][3] + args["pbox"][1]) / 2.0,
        ]
        # Set the width based on the pbox
        pbox_width = (
            (args["pbox"][2] - args["pbox"][0], axes_unit),
            (args["pbox"][3] - args["pbox"][1], axes_unit),
        )

    # Loop over all datasets in the time series
    if not args["no_mpi"]:
        yt.enable_parallelism()
    for ds in ts.piter(dynamic=True):
        if (
            hasattr(ds.fields.boxlib, "velocityx")
            and hasattr(ds.fields.boxlib, "velocityy")
            and hasattr(ds.fields.boxlib, "velocityz")
        ):
            utils.define_velocity_fields(ds)

        # Visualize the gradient field, if requested
        if args["gradient"]:
            vis_field = utils.get_gradient_field(ds, args["field"], args["gradient"])
        else:
            vis_field = args["field"]

        # Set index according to dict
        index = index_dict[str(ds)]

        fig = create_slice_plot(
            ds=ds,
            args=args,
            configs=configs,
            slc_center=slc_center,
            vis_field=vis_field,
            axes_unit=axes_unit,
            pbox_width=pbox_width if args["pbox"] else None,
            pbox_center=pbox_center if args["pbox"] else None,
            index=index,
            udf_funcs=udf_funcs,
            eb_var_name=eb_var_name,
        )

        plt_fname = f"""{vis_field}_{args["normal"]}_{str(index).zfill(5)}"""

        fig.tight_layout()
        fig.savefig(
            os.path.join(imgpath, f"{plt_fname}.png"),
            dpi=args["dpi"],
        )

        # Dump the figure handle as pickle for later modifications
        if args["pickle"]:
            with open(os.path.join(imgpath, f"{plt_fname}.pickle"), "wb") as f:
                pl.dump(fig, f)


if __name__ == "__main__":
    main()
