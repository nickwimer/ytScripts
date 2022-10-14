"""2D slice down the middle of the domain."""
import os
import pickle as pl
import sys

import numpy as np
import yt
from shapely.geometry import LineString, Point, Polygon
from skimage.measure import find_contours
from yt.units.yt_array import YTArray

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402


def get_args():
    """Parse command line arguments."""
    # Initialize the class for yt visualization arguments
    ytparse = ytargs.ytVisArgs()
    # Add in the arguments needed for SlicePlot
    ytparse.orientation_args()
    ytparse.vis_2d_args()
    ytparse.slice_args()
    # Return the parsed arguments
    return ytparse.parse_args()


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
    args = get_args()

    # Make the output directory for images
    if args.outpath:
        imgpath = args.outpath
    else:
        imgpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata/", "images"))
    os.makedirs(imgpath, exist_ok=True)

    # Override the units if needed
    if args.SI:
        units_override = {
            "length_unit": (1.0, "m"),
            "time_unit": (1.0, "s"),
            "mass_unit": (1.0, "kg"),
            "velocity_unit": (1.0, "m/s"),
        }
        axes_unit = "m"
    else:
        units_override = None
        axes_unit = "cm"

    # Load data files into dataset series
    ts, index_dict = utils.load_dataseries(
        datapath=args.datapath, pname=args.pname, units_override=units_override
    )

    # Get base attributes
    base_attributes = utils.get_attributes(ds=ts[0])

    # get number of cells in the level 0 non-EB grid
    if args.grid_info:
        dx0, dy0, dz0 = np.array(base_attributes["dxyz"])
        data = ts[0].covering_grid(
            level=0,
            left_edge=base_attributes["left_edge"],
            dims=base_attributes["dimensions"],
            ds=ts[0],
        )
        num_cells_0 = float(data["vfrac"].sum())
        domain_volume = dx0 * dy0 * dz0 * num_cells_0
        # left_edge = np.array(base_attributes["left_edge"])
        # right_edge = np.array(base_attributes["right_edge"])
        # Dx, Dy, Dz = right_edge - left_edge
        # domain_volume = Dx * Dy * Dz

    if args.verbose:
        print(f"""The fields in this dataset are: {base_attributes["field_list"]}""")

    # Set the center of the plot for loading the data
    if args.center is not None:
        slc_center = args.center
    else:
        # Set the center based on the plt data
        slc_center = (
            base_attributes["right_edge"] + base_attributes["left_edge"]
        ) / 2.0
        # provide slight offset to avoid grid alignment vis issues
        slc_center += YTArray(args.grid_offset, base_attributes["length_unit"])

    # Compute the center of the image for plotting
    if args.pbox:
        # Set the center based on the pbox
        pbox_center = [
            (args.pbox[2] + args.pbox[0]) / 2.0,
            (args.pbox[3] + args.pbox[1]) / 2.0,
        ]
        # Set the width based on the pbox
        pbox_width = (
            (args.pbox[2] - args.pbox[0], axes_unit),
            (args.pbox[3] - args.pbox[1], axes_unit),
        )
        # Set the left edge base on the pbox
        # pbox_left_edge = [args.pbox[0], args.pbox[1]]

        if args.contour:
            sys.exit("joint pbox and contour options are currently broken...")

    # Loop over all datasets in the time series
    yt.enable_parallelism()
    for ds in ts.piter(dynamic=True):

        # Get updated attributes for each plt file
        ds_attributes = utils.get_attributes(ds=ds)

        # Get the image slice resolution
        slc_res = {
            "x": (ds_attributes["resolution"][1], ds_attributes["resolution"][2]),
            "y": (ds_attributes["resolution"][2], ds_attributes["resolution"][0]),
            "z": (ds_attributes["resolution"][0], ds_attributes["resolution"][1]),
        }

        # Set index according to dict
        index = index_dict[str(ds)]

        # Plot the field
        slc = yt.SlicePlot(
            ds=ds,
            normal=args.normal,
            fields=args.field,
            center=slc_center,
            buff_size=tuple(args.buff)
            if args.buff is not None
            else slc_res[args.normal],
        )
        slc.set_axes_unit(axes_unit)
        slc.set_origin("native")

        if args.pbox is not None:
            slc.set_width(pbox_width)
            slc.set_center(pbox_center)
        if args.fbounds is not None:
            slc.set_zlim(args.field, args.fbounds[0], args.fbounds[1])
        slc.annotate_timestamp(draw_inset_box=True)
        if args.grids:
            if len(args.grids) > 0:
                slc.annotate_grids(
                    alpha=args.grids[0],
                    min_level=args.grids[1],
                    max_level=args.grids[2],
                    linewidth=args.grids[3],
                )
            else:
                slc.annotate_grids()
        slc.set_log(args.field, args.plot_log)
        slc.set_cmap(field=args.field, cmap=args.cmap)

        # Convert the slice to matplotlib figure
        fig = slc.export_to_mpl_figure(nrows_ncols=(1, 1))

        if args.contour is not None:
            xres, yres, zres = np.array(ds_attributes["resolution"])

            lx, ly, lz = np.array(ds_attributes["left_edge"])
            rx, ry, rz = np.array(ds_attributes["right_edge"])
            dx = (rx - lx) / xres
            dy = (ry - ly) / yres
            dz = (rz - lz) / zres

            # contour must be a multiple of three arguments
            if not len(args.contour) % 3 == 0:
                sys.exit(
                    "Contour argument must be a multiple of 3! [FIELD, VALUE, COLOR]"
                )
            else:
                num_contours = len(args.contour) // 3

            # Get the axes from the figure handle
            ax = fig.axes[0]

            for icnt in range(num_contours):
                if args.clw is None:
                    linewidth = 1.0
                else:
                    linewidth = args.clw[icnt]

                idx = icnt * 3
                contour = find_contours(
                    image=slc.frb[args.contour[idx]], level=args.contour[idx + 1]
                )

                if args.normal == "x":
                    plot_contours(
                        contour=contour,
                        ax=ax,
                        left_edge=[ly, lz],
                        dxy=[dy, dz],
                        color=args.contour[idx + 2],
                        linewidth=linewidth,
                    )
                elif args.normal == "y":
                    plot_contours(
                        contour=contour,
                        ax=ax,
                        left_edge=[lz, lx],
                        dxy=[dz, dx],
                        color=args.contour[idx + 2],
                        linewidth=linewidth,
                    )
                elif args.normal == "z":
                    plot_contours(
                        contour=contour,
                        ax=ax,
                        left_edge=[lx, ly],
                        dxy=[dx, dy],
                        color=args.contour[idx + 2],
                        linewidth=linewidth,
                    )
                else:
                    sys.exit(f"Normal {args.normal} is not in [x, y, z]!")

        plt_fname = f"{args.field}_{args.normal}_{str(index).zfill(5)}"

        if args.grid_info:

            dx0, dy0, dz0 = np.array(ds_attributes["dxyz"])

            level_data = ds.index.level_stats[0 : ds.index.max_level + 1]

            total_cells = 0
            cell_vol_percents = np.zeros(np.shape(level_data))
            for ilev, lev in enumerate(level_data):
                dx = dx0 / (2**ilev)
                dy = dy0 / (2**ilev)
                dz = dz0 / (2**ilev)
                total_cells += lev[1]
                cell_vol_percents[ilev] = lev[1] * dx * dy * dz / domain_volume * 100

            # Define text with grid info
            text_string = (
                f"Level 1 vol: {cell_vol_percents[1]:.0f}%\n"
                f"Level 2 vol: {cell_vol_percents[2]:.1f}%\n"
                f"Level 3 vol: {cell_vol_percents[3]:.1f}%\n"
                f"{total_cells*3/1e6:.0f}M  DOF"
            )
            # Add text
            ax.text(
                x=args.grid_info[0],
                y=args.grid_info[1],
                s=text_string,
                color="white",
                bbox=dict(facecolor="black", edgecolor="white", boxstyle="round"),
            )

        if args.rm_eb:
            # plot over the EB surface with white
            cline = ax.get_children()[11].get_data()
            ax.fill_between(
                cline[0], base_attributes["left_edge"][1], cline[1], color="grey"
            )
            ax.fill_betweenx(
                np.linspace(
                    base_attributes["left_edge"][1],
                    base_attributes["right_edge"][1],
                    11,
                ),
                base_attributes["left_edge"][0],
                cline[0][0],
                color="grey",
            )
            ax.fill_betweenx(
                np.linspace(
                    base_attributes["left_edge"][1],
                    base_attributes["right_edge"][1],
                    11,
                ),
                cline[0][-1],
                base_attributes["right_edge"][0],
                color="grey",
            )

        if args.levels:
            level_points = {}
            level_lines = {}

            left_edge = ds_attributes["left_edge"]
            right_edge = ds_attributes["right_edge"]
            data_source = ds.box(
                left_edge=[0, left_edge[1], left_edge[2]],
                right_edge=[0, right_edge[1], right_edge[2]],
            )

            for igrid, g in enumerate(data_source.index.grids):
                level = g.Level
                if level >= args.levels[0] and level <= args.levels[1]:
                    g_corn = data_source.index.grid_corners[:, :, igrid]

                    x_mean = np.mean(g_corn[:, 0])
                    y_min = np.min(g_corn[:, 1])
                    y_max = np.max(g_corn[:, 1])
                    z_min = np.min(g_corn[:, 2])
                    z_max = np.max(g_corn[:, 2])

                    x_mean = round(x_mean, 1)

                    # four points
                    P1 = Point(y_min, z_min)
                    P2 = Point(y_min, z_max)
                    P3 = Point(y_max, z_min)
                    P4 = Point(y_max, z_max)

                    # four lines
                    L1 = LineString([P1, P2])
                    L2 = LineString([P2, P4])
                    L3 = LineString([P4, P3])
                    L4 = LineString([P3, P1])

                    if x_mean == 0:
                        if level in level_points:
                            level_points[level].append(P1)
                            level_points[level].append(P2)
                            level_points[level].append(P3)
                            level_points[level].append(P4)
                        else:
                            level_points[level] = [P1]
                            level_points[level].append(P2)
                            level_points[level].append(P3)
                            level_points[level].append(P4)

                        # determine if we should add a line based on the points

                        if level in level_lines:
                            level_lines[level].append(L1)
                            level_lines[level].append(L2)
                            level_lines[level].append(L3)
                            level_lines[level].append(L4)
                        else:
                            level_lines[level] = [L1]
                            level_lines[level].append(L2)
                            level_lines[level].append(L3)
                            level_lines[level].append(L4)

            alph = np.linspace(
                0.2, 0.8, (int(args.levels[1]) - int(args.levels[0]) + 1)
            )
            for ilev, lev in enumerate(np.arange(args.levels[0], args.levels[1] + 1)):
                poly = Polygon([(point.x, point.y) for point in level_points[lev]])
                xx, yy = poly.exterior.coords.xy

                ax.scatter(xx, yy, marker="*")

                # poly2 = Polygon([(line.x, line.y) for line in level_lines[lev]])
                # ax.plot(*poly2.boundary.coords.xy)
                # mls = MultiLineString(level_lines[lev])

                # ax.plot(*mls.bounds)
                # ax.plot(*mls.boundary.coords.xy)

                for line in level_lines[lev]:
                    ax.plot(*line.xy, color="black", alpha=alph[ilev])

        fig.tight_layout()
        fig.savefig(
            os.path.join(imgpath, f"{plt_fname}.png"),
            dpi=args.dpi,
        )

        # Dump the figure handle as pickle for later modifications
        if args.pickle:
            with open(os.path.join(imgpath, f"{plt_fname}.pickle"), "wb") as f:
                pl.dump(fig, f)


if __name__ == "__main__":
    main()
