"""Load averages from npz and plot."""
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.ytargs as ytargs  # noqa: E402


def get_args():
    """Parse command line arguments."""
    # Initialize the class for plotting
    ytparse = ytargs.ytPlotArgs()
    # Add in the arguments for the plot averages
    ytparse.average_args()
    # Return the parsed arguments
    return ytparse.parse_args()


def main():

    # Get arguments
    args = get_args()

    # Create the output directory
    if args.outpath:
        imgpath = args.outpath
    else:
        imgpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata", "images"))
    os.makedirs(imgpath, exist_ok=True)

    # Inputs for plotting
    fx = 6
    fy = 5

    fig, ax = plt.subplots(1, 1, figsize=(fx, fy))

    df = pd.read_pickle(os.path.join(args.datapath, f"{args.fname[0]}.pkl"))
    # df["mix_frac"] = np.linspace(0, 1, len(df["temp_bins"]))
    len_temp_bins = len(df.columns) - 1
    mix_frac = np.linspace(0, 1, len_temp_bins + 1)
    bin_centers = np.zeros(len_temp_bins)
    temp_centers = np.zeros(len_temp_bins)
    for i in range(len(bin_centers)):
        bin_centers[i] = 0.5 * (mix_frac[i] + mix_frac[i + 1])
        temp_centers[i] = df[f"temp_bin_{i}"].values

    ax.scatter(bin_centers, temp_centers, marker="*")

    # df["mix_frac"] = bin_centers
    # df.plot(ax=ax, x="mix_frac", y="temp_bins", marker="*", kind="scatter")

    fig.savefig(os.path.join(imgpath, f"""mixture_frac_temp.png"""), dpi=args.dpi)

    # for field in args.fields:

    #     fig, ax = plt.subplots(1, 1, figsize=(fx, fy))

    #     for fname in args.fname:
    #         # Load the dataframe
    #         df = pd.read_pickle(os.path.join(args.datapath, f"{fname}.pkl"))
    #         df.plot(
    #             x="mix_frac",
    #             y=field,
    #             ax=ax,
    #             label=f"""{fname} {field}""",
    #             marker="*",
    #             kind="scatter",
    #         )
    #         ax.set_xlabel("time (s)")
    #         ax.set_ylabel(field)
    #         ax.set_title("Domain Average vs. Time")

    #     fig.savefig(
    #         os.path.join(imgpath, f"""average_{field}_{'_'.join(args.fname)}.png"""),
    #         dpi=args.dpi,
    #     )


if __name__ == "__main__":
    main()
