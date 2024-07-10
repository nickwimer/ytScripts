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

if utils.is_latex_available():
    plt.rc("text", usetex=True)
else:
    print("LaTeX not available, using standard font.")


def get_parser():
    """Get the parser."""
    ytparse = ytargs.ytVisArgs()
    # Add in the arguments needed for SlicePlot
    ytparse.orientation_args()
    ytparse.vis_2d_args()
    ytparse.slice_args()

    return ytparse


def get_args(parser):
    """Get the arguments from the parser."""
    args = parser.parse_args()

    # Get the initial set of arguments
    init_args = parser.parse_args()

    # Override the command-line arguments with the input file
    if init_args.ifile:
        args = parser.override_args(init_args, init_args.ifile)
    else:
        args = vars(init_args)

    # Return the parsed arguments as a dict
    return args


def plot_contours(contour, ax, left_edge, dxy, color, linewidth):
    """Add contours to plot axes."""

    for icnt in contour:
        ax.plot(
            icnt[:, 1] * dxy[0] + left_edge[0],
            icnt[:, 0] * dxy[1] + left_edge[1],
            alpha=1.0,
            color=color,
            zorder=10,
            linewidth=linewidth,
        )


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

    # Enable tex parsing for plots
    if args["use_tex"]:
        plt.rc("text", usetex=True)

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

    # get number of cells in the level 0 non-EB grid
    if args["grid_info"]:
        dx0, dy0, dz0 = np.array(base_attributes["dxyz"])
        data = ts[0].covering_grid(
            level=0,
            left_edge=base_attributes["left_edge"],
            dims=base_attributes["dimensions"],
            ds=ts[0],
        )
        num_cells_0 = float(data[eb_var_name].sum())
        domain_volume = dx0 * dy0 * dz0 * num_cells_0
        # left_edge = np.array(base_attributes["left_edge"])
        # right_edge = np.array(base_attributes["right_edge"])
        # Dx, Dy, Dz = right_edge - left_edge
        # domain_volume = Dx * Dy * Dz

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
        # Set the left edge base on the pbox
        # pbox_left_edge = [args.pbox[0], args.pbox[1]]

        if args["contour"]:
            sys.exit("joint pbox and contour options are currently broken...")

    # Loop over all datasets in the time series
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

        # Get updated attributes for each plt file
        ds_attributes = utils.get_attributes(ds=ds)

        # Get the image slice resolution
        slc_res = {
            "x": (ds_attributes["resolution"][1], ds_attributes["resolution"][2]),
            "y": (ds_attributes["resolution"][2], ds_attributes["resolution"][0]),
            "z": (ds_attributes["resolution"][0], ds_attributes["resolution"][1]),
        }

        if args["normal"] == "y":
            max_res = max(
                ds_attributes["resolution"][2], ds_attributes["resolution"][0]
            )
            slc_res["y"] = (max_res, max_res)

        # Set index according to dict
        index = index_dict[str(ds)]

        # Plot the field
        slc = yt.SlicePlot(
            ds=ds,
            normal=args["normal"],
            fields=vis_field,
            center=slc_center,
            buff_size=(
                tuple(args["buff"])
                if args["buff"] is not None
                else slc_res[args["normal"]]
            ),
        )
        if args["normal"] == "y":
            slc.swap_axes()
        slc.set_axes_unit(axes_unit)
        slc.set_origin("native")

        if args["pbox"] is not None:
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
            norm_dict = {"x": ["y", "z"], "y": ["x", "z"], "z": ["x", "y"]}
            slc.set_colorbar_label(
                field=vis_field,
                label=(
                    configs["vis_field_attrs"][vis_field]["label"]
                    if vis_field in configs["vis_field_attrs"]
                    else vis_field
                ),
            )
            # if not configs["cbar_attrs"]["label"]["loc"] == "right":
            # slc.set_colorbar_label(field=vis_field, label="")
            slc.set_xlabel(f"""${norm_dict[args["normal"]][0]}$""")
            slc.set_ylabel(f"""${norm_dict[args["normal"]][1]}$""")

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

        if args["contour"] is not None:
            xres, yres, zres = np.array(ds_attributes["resolution"])

            lx, ly, lz = np.array(ds_attributes["left_edge"])
            rx, ry, rz = np.array(ds_attributes["right_edge"])
            dx = (rx - lx) / xres
            dy = (ry - ly) / yres
            dz = (rz - lz) / zres

            # contour must be a multiple of three arguments
            if not len(args["contour"]) % 3 == 0:
                sys.exit(
                    "Contour argument must be a multiple of 3! [FIELD, VALUE, COLOR]"
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
                contour = find_contours(
                    image=slc.frb[args["contour"][idx]], level=args["contour"][idx + 1]
                )

                if args["normal"] == "x":
                    plot_contours(
                        contour=contour,
                        ax=ax,
                        left_edge=[ly, lz],
                        dxy=[dy, dz],
                        color=args["contour"][idx + 2],
                        linewidth=linewidth,
                    )
                elif args["normal"] == "y":
                    plot_contours(
                        contour=contour,
                        ax=ax,
                        left_edge=[lz, lx],
                        dxy=[dz, dx],
                        color=args["contour"][idx + 2],
                        linewidth=linewidth,
                    )
                elif args["normal"] == "z":
                    plot_contours(
                        contour=contour,
                        ax=ax,
                        left_edge=[lx, ly],
                        dxy=[dx, dy],
                        color=args["contour"][idx + 2],
                        linewidth=linewidth,
                    )
                else:
                    sys.exit(f"""Normal {args["normal"]} is not in [x, y, z]!""")

        plt_fname = f"""{vis_field}_{args["normal"]}_{str(index).zfill(5)}"""

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

            # Define text with grid info
            text_string = ""
            for ilev in np.arange(args["grid_info"][2], args["grid_info"][3] + 1):
                text_string += (
                    f"Level {int(ilev)} vol: {cell_vol_percents[int(ilev)]:.1f}%\n"
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

        # Remove the EB boundary defined by vfrac < 0.5
        if args["rm_eb"]:
            if args["pbox"]:
                extent = [
                    args["pbox"][0],
                    args["pbox"][2],
                    args["pbox"][1],
                    args["pbox"][3],
                ]
            else:
                lx, ly, lz = np.array(ds_attributes["left_edge"])
                rx, ry, rz = np.array(ds_attributes["right_edge"])

                if args["normal"] == "x":
                    extent = [ly, ry, lz, rz]
                elif args["normal"] == "y":
                    extent = [lz, rz, lx, rx]
                elif args["normal"] == "z":
                    extent = [lx, rx, ly, ry]

            # TODO: move the default rm_eb function into utils of top of script
            if "rm_eb" in udf_funcs:
                ax = udf_funcs["rm_eb"](ax)
            else:
                vfrac = slc.frb[("boxlib", eb_var_name)].to_ndarray()
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
