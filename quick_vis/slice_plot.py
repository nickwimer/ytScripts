"""2D slice down the middle of the domain."""
import argparse
import os
import sys

import yt
from yt.units.yt_array import YTArray

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402


def get_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--datapath",
        type=str,
        required=True,
        help="Path to the plt files for visualization",
    )
    parser.add_argument(
        "-o",
        "--outpath",
        type=str,
        required=False,
        default=None,
        help="Path to the output image directory (defualt to datapath/images)",
    )
    parser.add_argument(
        "--pname",
        type=str,
        required=False,
        default=None,
        help="Name of plt files to plot (if empty, do all)",
        nargs="+",
    )
    parser.add_argument(
        "--field",
        type=str,
        required=True,
        help="Name of the field for visualization",
    )
    parser.add_argument(
        "--normal",
        type=str,
        required=True,
        help="Normal direction for the slice plot",
    )
    parser.add_argument(
        "-c",
        "--center",
        nargs="+",
        type=float,
        required=False,
        help="Coordinate list for center of slice plot",
    )
    parser.add_argument(
        "--fbounds",
        nargs="+",
        type=float,
        required=False,
        default=None,
        help="Bounds to plot the field",
    )
    parser.add_argument(
        "--cmap",
        type=str,
        required=False,
        default="dusk",
        help="Colormap for the SlicePlot",
    )
    parser.add_argument(
        "--LM",
        action="store_true",
        help="flag to identify if this is a low Mach simulation",
    )
    parser.add_argument("--plot_log", action="store_true", help="plot in log values")
    parser.add_argument(
        "--grids",
        action="store_true",
        help="flag to turn on grid annotation",
    )
    parser.add_argument(
        "--grid_offset",
        type=float,
        default=0.0,
        required=False,
        help="Amount to offset center to avoid grid alignment vis issues",
    )
    parser.add_argument(
        "--buff",
        type=int,
        default=None,
        nargs="+",
        required=False,
        help="buffer for the sliceplot image for plotting",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        required=False,
        help="dpi of the output image",
    )
    parser.add_argument(
        "--pbox",
        type=float,
        nargs="+",
        default=None,
        required=False,
        help="Bounding box of the plot specified by the two corners (x0 y0 x1 y1)",
    )
    return parser.parse_args()


def main():

    # Parse the input arguments
    args = get_args()

    # Make the output directory for images
    imgpath = os.path.join(args.datapath, "images/")
    if not os.path.exists(imgpath):
        os.makedirs(imgpath)

    # Override the units if needed
    if args.LM:
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
    ts, index_list = utils.load_dataseries(
        datapath=args.datapath, pname=args.pname, units_override=units_override
    )

    # Get base attributes
    base_attributes = utils.get_attributes(ds=ts[0])

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

    # Loop over all datasets in the time series
    idx = 0
    for ds in ts:

        # Get updated attributes for each plt file
        ds_attributes = utils.get_attributes(ds=ds)

        # Get the image slice resolution
        slc_res = {
            "x": (ds_attributes["resolution"][1], ds_attributes["resolution"][2]),
            "y": (ds_attributes["resolution"][0], ds_attributes["resolution"][2]),
            "z": (ds_attributes["resolution"][0], ds_attributes["resolution"][1]),
        }

        # Set index according to load method
        if args.pname is not None:
            index = index_list[idx]
        else:
            index = idx

        # Plot the field
        slc = yt.SlicePlot(
            ds,
            args.normal,
            args.field,
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
            slc.annotate_grids()
        slc.set_log(args.field, args.plot_log)
        slc.set_cmap(field=args.field, cmap=args.cmap)

        # Save the image
        slc.save(
            os.path.join(
                imgpath, f"""{args.field}_{args.normal}_{str(index).zfill(5)}.png"""
            ),
            mpl_kwargs=dict(dpi=args.dpi),
        )

        # increment the loop idx
        idx += 1


if __name__ == "__main__":
    main()
