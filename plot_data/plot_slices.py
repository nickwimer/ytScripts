"""Load slices from npz and plot."""
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402


def get_args():
    """Parse command line arguments."""
    # Initialize the base yt class
    ytparse = ytargs.ytArgs()
    # Add in the arguments for plotting 2D
    ytparse.vis_2d_args()
    return ytparse.parse_args()


def main():

    # Parse the input arguments
    args = get_args()

    # Create the output directory
    imgpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata", "images"))
    os.makedirs(imgpath, exist_ok=True)

    # Get list of files in the data directory
    files = np.sort(os.listdir(args.datapath))

    # Loop over files, plot and save images
    index = 0
    for fname in files:

        # Load the data
        data = np.load(os.path.join(args.datapath, fname), allow_pickle=True)
        # Print out the variables in the dataset
        if index == 0:
            print(f"""The variables contained in this file are: {data.files}""")

        # Unpack the dicts
        ds_attributes = data["ds_attributes"][()]
        slices = data["slices"][()]
        # fields = data["fields"][()]

        # Inputs for plotting
        ylen, xlen = slices[args.field].shape
        fx, fy = utils.get_fig_aspect_ratio(xlen, ylen, base=3)

        # Get some variables
        normal = data["normal"]
        iloc = data["iloc"]
        time = ds_attributes["time"]
        length_unit = ds_attributes["length_unit"]

        if args.field not in data["fields"]:
            sys.exit(f"""{args.field} not in {data["fields"]}""")

        fig, ax = plt.subplots(1, 1, figsize=(fx, fy))

        if normal == "x":
            y = np.linspace(
                ds_attributes["left_edge"][1], ds_attributes["right_edge"][1], xlen
            )
            z = np.linspace(
                ds_attributes["left_edge"][2], ds_attributes["right_edge"][2], ylen
            )
            Y, Z = np.meshgrid(y, z, indexing="xy")
            im = ax.pcolormesh(Y, Z, slices[args.field])
            ax.set_xlabel(f"y ({length_unit.units})")
            ax.set_ylabel(f"z ({length_unit.units})")
        elif normal == "y":
            x = np.linspace(
                ds_attributes["left_edge"][0], ds_attributes["right_edge"][0], xlen
            )
            z = np.linspace(
                ds_attributes["left_edge"][2], ds_attributes["right_edge"][2], ylen
            )
            X, Z = np.meshgrid(x, z, indexing="ij")
            im = ax.pcolormesh(X, Z, slices[args.field])
            ax.set_xlabel(f"x ({length_unit.units})")
            ax.set_ylabel(f"z ({length_unit.units})")
        elif normal == "z":
            x = np.linspace(
                ds_attributes["left_edge"][0], ds_attributes["right_edge"][0], xlen
            )
            y = np.linspace(
                ds_attributes["left_edge"][1], ds_attributes["right_edge"][1], ylen
            )
            X, Y = np.meshgrid(x, y, indexing="ij")
            im = ax.pcolormesh(X, Y, slices[args.field])
            ax.set_xlabel(f"x ({length_unit.units})")
            ax.set_ylabel(f"y ({length_unit.units})")
        else:
            sys.exit(f"Normal {normal} not in: [x, y, z]")

        ax.set_title(
            f"""{normal} = {iloc:.4f}, time = {float(time.in_units("ms")):.2f} ms"""
        )
        ax.set_aspect("equal")
        fig.colorbar(im, ax=ax)

        fig.savefig(
            os.path.join(imgpath, f"""{args.field}_{normal}{iloc:.4f}_{index}.png"""),
            dpi=args.dpi,
        )

        index += 1


if __name__ == "__main__":
    main()
