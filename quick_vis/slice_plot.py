"""2D slice down the middle of the domain."""
import argparse
import os

import yt

if __name__ == "__main__":

    # Parse the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--datapath",
        type=str,
        required=True,
        help="Path to the plt files for visualization",
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
        "--fbounds",
        type=list,
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
    args = parser.parse_args()

    # Get the current directory
    cwd = os.getcwd()

    # Make the output directory for images
    imgpath = os.path.join(cwd, "images/")
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

    # Load the plt files
    ts = yt.load(
        os.path.join(args.datapath, "plt?????"),
        units_override=units_override,
    )

    ds0 = ts[0]
    length_unit = ds0.length_unit
    print(f"The fields in this dataset are: {ds0.field_list}")

    index = 0
    for ds in ts:

        # Plot the field
        slc = yt.SlicePlot(ds, args.normal, args.field)
        slc.set_axes_unit(axes_unit)
        if args.fbounds is not None:
            slc.set_zlim(args.field, args.fbounds[0], args.fbounds[1])
        slc.annotate_timestamp()
        slc.set_log(args.field, args.plot_log)
        slc.set_cmap(field=args.field, cmap=args.cmap)

        # Save the image
        slc.save(os.path.join(imgpath, f"""{args.field}_{str(index).zfill(5)}.png"""))

        index += 1
