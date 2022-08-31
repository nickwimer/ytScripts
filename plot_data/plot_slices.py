"""Load slices from npz and plot."""
import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        required=True,
        help="Path to the npz data to load",
    )
    args = parser.parse_args()

    # Get current directory
    cwd = os.getcwd()

    # Create the output directory
    imgpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata", "images"))
    os.makedirs(imgpath, exist_ok=True)

    # Get list of files in the data directory
    files = np.sort(os.listdir(args.path))

    # Inputs for the plotting
    fx = 6
    fy = 5

    # Loop over files, plot and save images
    index = 0
    for fname in files:

        # Load the data
        data = np.load(os.path.join(args.path, fname))
        if index == 0:
            print(f"""The variables contained in this file are: {data.files}""")

        fig, ax = plt.subplots(1, 1, figsize=(fx, fy))

        im = ax.pcolormesh(data["var_slice"])
        ax.set_xlabel("y")
        ax.set_ylabel("z")
        ax.set_title(f"""x = {data["xloc"]:.4f}, time = {data["time"]*1e3:.2f} ms""")
        fig.colorbar(im, ax=ax)

        fig.savefig(
            os.path.join(
                imgpath, f"""{data["field"]}_x{data["xloc"]:.4f}_{index}.png"""
            ),
            dpi=300,
        )

        index += 1
