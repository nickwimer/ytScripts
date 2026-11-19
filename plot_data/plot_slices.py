"""Load slices from npz and plot."""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402


def get_parser():
    """Get the parser."""
    ytparse = ytargs.ytPlotArgs()
    # Add in the arguments for the plot slices
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


# The axes across and up the image for each axis normal
AXIS_LAYOUT = {"x": ("y", "z"), "y": ("x", "z"), "z": ("x", "y")}


def image_layout(data, xlen, ylen):
    """Return where the pixels of a saved slice sit and how to label them.

    Returns the pixel positions across and up the image, the labels of those
    directions, the pixel sizes across and up, and the name of the slice position.
    Diagonal slices are measured from their center, along the directions saved with
    them.
    """
    normal = str(data["normal"])
    if "normal_vector" in data.files:
        left, right, bottom, top = data["bounds"]
        dh, dv = (right - left) / xlen, (top - bottom) / ylen
        h = left + (np.arange(xlen) + 0.5) * dh
        v = bottom + (np.arange(ylen) + 0.5) * dv
        hlabel, vlabel = (f"${label}$" for label in data["labels"])
        return h, v, hlabel, vlabel, dh, dv, f"{normal}: d"

    if normal not in AXIS_LAYOUT:
        sys.exit(f"Normal {normal} not in: [x, y, z]")
    ds_attributes = data["ds_attributes"][()]
    ih, iv = ("xyz".index(axis) for axis in AXIS_LAYOUT[normal])
    h = np.linspace(
        ds_attributes["left_edge"][ih], ds_attributes["right_edge"][ih], xlen
    )
    v = np.linspace(
        ds_attributes["left_edge"][iv], ds_attributes["right_edge"][iv], ylen
    )
    dxyz = ds_attributes["dxyz"]
    hlabel, vlabel = AXIS_LAYOUT[normal]
    return h, v, hlabel, vlabel, dxyz[ih], dxyz[iv], normal


def main():
    # Parse the input arguments
    parser = get_parser()
    args = get_args(parser)

    # Create the output directory
    if args["outpath"]:
        imgpath = args["outpath"]
    else:
        imgpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata", "images"))
    os.makedirs(imgpath, exist_ok=True)

    # Get list of files in the data directory
    files = np.sort(os.listdir(args["datapath"]))

    # Loop over files, plot and save images
    index = 0
    for fname in files:

        # Load the data
        data = np.load(os.path.join(args["datapath"], fname), allow_pickle=True)
        # Print out the variables in the dataset
        if index == 0 and args["verbose"]:
            print(f"""The variables contained in this file are: {data.files}""")

        # Unpack the dicts
        ds_attributes = data["ds_attributes"][()]
        slices = data["slices"][()]
        # fields = data["fields"][()]

        # Get some variables
        normal = data["normal"]
        iloc = data["iloc"]
        time = ds_attributes["time"]
        length_unit = ds_attributes["length_unit"]

        if args["field"] not in data["fields"]:
            sys.exit(f"""{args["field"]} not in {data["fields"]}""")

        # Inputs for plotting
        ylen, xlen = slices[args["field"]].shape
        h, v, hlabel, vlabel, dh, dv, where = image_layout(data, xlen, ylen)

        if args["pbox"] is None:
            fx, fy = utils.get_fig_aspect_ratio(xlen, ylen, base=5)
        else:
            fx, fy = utils.get_fig_aspect_ratio(
                xlen=(args["pbox"][2] - args["pbox"][0]) / dh,
                ylen=(args["pbox"][3] - args["pbox"][1]) / dv,
                base=3,
            )

        # Set the figure and axes
        fig, ax = plt.subplots(1, 1, figsize=(fx, fy))
        # Set the colormap
        cmap = plt.get_cmap(args["cmap"])

        H, V = np.meshgrid(h, v, indexing="xy")
        im = ax.pcolormesh(
            H,
            V,
            slices[args["field"]],
            cmap=cmap,
            vmin=args["fbounds"][0] if args["fbounds"] else None,
            vmax=args["fbounds"][1] if args["fbounds"] else None,
        )
        ax.set_xlabel(f"{hlabel} ({length_unit.units})")
        ax.set_ylabel(f"{vlabel} ({length_unit.units})")

        ax.set_title(
            f"""{where} = {iloc:.4f} {length_unit.units}, """
            f"""time = {float(time.in_units("ms")):.2f} ms"""
        )
        if args["pbox"]:
            ax.set_xlim(args["pbox"][0], args["pbox"][2])
            ax.set_ylim(args["pbox"][1], args["pbox"][3])
        else:
            ax.set_aspect("equal")

        fig.tight_layout()
        fig.colorbar(im, ax=ax)

        fig.savefig(
            os.path.join(
                imgpath, f"""{args["field"]}_{normal}{iloc:.4f}_{index}.png"""
            ),
            dpi=args["dpi"],
        )

        index += 1


if __name__ == "__main__":
    main()
