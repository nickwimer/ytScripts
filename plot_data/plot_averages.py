"""Load averages from npz and plot."""
import argparse
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd


def get_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        required=True,
        help="Path to the pkl data to load and plot",
    )
    parser.add_argument(
        "-f",
        "--fname",
        type=str,
        required=True,
        help="Name of the pkl file to load and plot",
        nargs="+",
    )
    parser.add_argument(
        "--field",
        type=str,
        required=True,
        help="Name of the fields to plot",
        nargs="+",
    )
    return parser.parse_args()


def main():

    # Get arguments
    args = get_args()

    # Create the output directory
    imgpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata", "images"))
    os.makedirs(imgpath, exist_ok=True)

    # Inputs for plotting
    fx = 6
    fy = 5

    for field in args.field:

        fig, ax = plt.subplots(1, 1, figsize=(fx, fy))

        for fname in args.fname:
            # Load the dataframe
            df = pd.read_pickle(os.path.join(args.path, f"{fname}.pkl"))

            df.plot(x="time", y=field, ax=ax, label=f"""{fname} {field}""", marker="*")
            ax.set_xlabel("time (s)")
            ax.set_ylabel(field)
            ax.set_title("Domain Average vs. Time")

        fig.savefig(
            os.path.join(imgpath, f"""average_{field}_{'_'.join(args.fname)}.png"""),
            dpi=300,
        )


if __name__ == "__main__":
    main()
