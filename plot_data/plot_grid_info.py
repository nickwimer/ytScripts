"""Load grid info from pickle and plot."""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.ytargs as ytargs  # noqa: E402


def get_parser():
    """Get the parser."""
    ytparse = ytargs.ytPlotArgs()
    # Add in the arguments for the plot grid info
    ytparse.grid_args()

    return ytparse


def get_base_parser():
    """Get the base level parser primarily for documentation."""
    return get_parser().get_parser()


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

    # Load the dataframe
    df = pd.read_pickle(os.path.join(args["datapath"], f"""{args["fname"]}.pkl"""))

    # Sort the dataframe by time
    df.sort_values(by="time", inplace=True, ignore_index=True)

    time = df["time"].values
    max_levels = df.loc[0, "grid_data"].index.size

    # Add some additional fields
    cell_tot_percents = np.zeros((np.size(time), max_levels))
    cell_vol_percents = np.zeros((np.size(time), max_levels))

    # domain volume
    dx0, dy0, dz0 = np.array(df.attrs["base_attributes"]["dxyz"])
    left_edge = np.array(df.attrs["base_attributes"]["left_edge"])
    right_edge = np.array(df.attrs["base_attributes"]["right_edge"])
    Dx, Dy, Dz = right_edge - left_edge
    domain_volume = Dx * Dy * Dz

    for idx, cell in df.iterrows():

        total_cells = cell["grid_data"]["numcells"].sum()

        for ilev, lev_cell in cell["grid_data"].iterrows():
            dx = dx0 / (2**ilev)
            dy = dy0 / (2**ilev)
            dz = dz0 / (2**ilev)
            cell["grid_data"].loc[ilev, "percent"] = (
                lev_cell["numcells"] / total_cells * 100
            )

            cell_tot_percents[idx, ilev] = lev_cell["numcells"] / total_cells * 100
            cell_vol_percents[idx, ilev] = (
                lev_cell["numcells"] * dx * dy * dz / domain_volume * 100
            )

    # Inputs for plotting
    fx = 6
    fy = 5

    if args["ptype"] == "line":

        # Create the figure and axes
        fig, ax = plt.subplots(1, 1, figsize=(fx, fy))

        # Make simple line plot
        for lev in range(np.max(max_levels)):
            ax.plot(
                time,
                cell_tot_percents[:, lev],
                label=f"level {lev}",
                marker="o",
                linestyle="-",
                markersize=4,
            )

        ax.legend()
        ax.set_xlabel("time (s)")
        ax.set_ylabel(r"num cells %")

        fig.savefig(os.path.join(imgpath, "num_cells_percent.png"), dpi=args["dpi"])

        # Create the figure and axes
        fig, ax = plt.subplots(1, 1, figsize=(fx, fy))

        # Make simple line plot
        for lev in range(np.max(max_levels)):
            ax.plot(
                time,
                cell_vol_percents[:, lev],
                label=f"level {lev}",
                marker="o",
                linestyle="-",
                markersize=4,
            )

        ax.set_ylim(0, np.max(cell_vol_percents[:, 1]))
        ax.legend()
        ax.set_xlabel("time (s)")
        ax.set_ylabel(r"volume domain %")

        fig.savefig(os.path.join(imgpath, "vol_domain_percent.png"), dpi=args["dpi"])


if __name__ == "__main__":
    main()
