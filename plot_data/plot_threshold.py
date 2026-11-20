"""Load the cells above a threshold from pkl and plot them in 3D."""

import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm, Normalize
from matplotlib.ticker import MaxNLocator

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402, F401 (registers the yt colormaps)
import ytscripts.ytargs as ytargs  # noqa: E402


def get_parser():
    """Get the parser."""
    ytparse = ytargs.ytPlotArgs()
    # Add in the arguments for the plot threshold
    ytparse.threshold_args()

    return ytparse


def get_base_parser():
    """Get the base level parser primarily for documentation."""
    return get_parser().get_parser()


def get_args(parser, cli_args=None):
    """Get the arguments from the parser (cli_args defaults to sys.argv)."""
    # Parse the command line, merged with the input file if one is given
    args = parser.get_args(cli_args)

    if args["fbounds"] is not None and len(args["fbounds"]) != 2:
        parser.get_parser().error("--fbounds needs two values: min max")

    if len(args["view"]) != 2:
        parser.get_parser().error("--view needs two values: elevation azimuth")

    if args["bounds"] is not None:
        if len(args["bounds"]) != 6:
            parser.get_parser().error(
                "--bounds needs six values: xlo ylo zlo xhi yhi zhi"
            )
        if any(lo >= hi for lo, hi in zip(args["bounds"][:3], args["bounds"][3:])):
            parser.get_parser().error("--bounds needs each low value below its high")

    if args["max_points"] < 1:
        parser.get_parser().error("--max_points must be at least 1")

    # Return the parsed arguments as a dict
    return args


def find_threshold_files(datapath, fnames=None):
    """Return the paths of the threshold files to plot."""
    if fnames:
        return [
            os.path.join(datapath, f if f.endswith(".pkl") else f"{f}.pkl")
            for f in fnames
        ]
    return sorted(glob.glob(os.path.join(datapath, "threshold_*.pkl")))


def select_cells(df, bounds=None, max_points=None, seed=0):
    """Return the cells inside the bounds, randomly thinned to max_points."""
    if bounds is not None:
        inside = np.ones(len(df), dtype=bool)
        for axis, lo, hi in zip("xyz", bounds[:3], bounds[3:]):
            inside &= (df[axis] >= lo).to_numpy() & (df[axis] <= hi).to_numpy()
        df = df[inside]

    if max_points is not None and len(df) > max_points:
        df = df.sample(n=max_points, random_state=seed)

    return df


def marker_sizes(df, psize):
    """Return marker areas that grow with the cell size, psize for the finest."""
    dx = df["dx"].to_numpy()
    if len(dx) == 0:
        return dx
    return psize * (dx / dx.min()) ** 2


def axis_limits(df, bounds=None):
    """Return the (lo, hi) limits of x, y and z, from the bounds or the cells.

    The cells are given half a cell of room on each side.
    """
    if bounds is not None:
        return [(lo, hi) for lo, hi in zip(bounds[:3], bounds[3:])]

    limits = []
    for axis in "xyz":
        pos = df[axis].to_numpy()
        half = df[f"d{axis}"].to_numpy() / 2.0
        limits.append(((pos - half).min(), (pos + half).max()))
    return limits


def color_norm(values, fbounds=None, plot_log=False):
    """Return the color normalization for the values."""
    vmin, vmax = fbounds if fbounds else (None, None)
    if plot_log:
        if vmin is None:
            positive = values[values > 0]
            vmin = positive.min() if len(positive) else None
        return LogNorm(vmin=vmin, vmax=vmax)
    return Normalize(vmin=vmin, vmax=vmax)


def unit_label(units):
    """Return the units for a label, or an empty string if there are none."""
    if units in (None, "", "dimensionless"):
        return ""
    return f" ({units})"


def plot_threshold(df, field, args):
    """Make the 3D figure of the cells and return it."""
    attrs = df.attrs
    units = attrs.get("units", {})

    cells = select_cells(df, bounds=args["bounds"], max_points=args["max_points"])
    if len(cells) < len(df):
        print(f"Plotting {len(cells)} of the {len(df)} cells.")

    values = cells[field].to_numpy()

    # Set the figure and axes
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(projection="3d")
    # Set the colormap
    cmap = plt.get_cmap(args["cmap"])

    im = ax.scatter(
        cells["x"],
        cells["y"],
        cells["z"],
        c=values,
        s=marker_sizes(cells, args["psize"]),
        cmap=cmap,
        norm=color_norm(values, args["fbounds"], args["plot_log"]),
        marker="o",
        linewidths=0,
        depthshade=False,
    )

    # Draw the box with each axis to the same scale
    limits = axis_limits(cells, args["bounds"])
    for setter, (lo, hi) in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), limits):
        setter(lo, hi)
    ax.set_box_aspect([hi - lo for lo, hi in limits])
    ax.view_init(elev=args["view"][0], azim=args["view"][1], vertical_axis=args["up"])

    for setter, axis in zip((ax.set_xlabel, ax.set_ylabel, ax.set_zlabel), "xyz"):
        setter(f"{axis}{unit_label(units.get(axis))}")
    # Fewer ticks so the labels do not run into each other
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_major_locator(MaxNLocator(nbins=5))

    # Describe the threshold in the title
    title = f"""{attrs.get("field", field)} > {attrs.get("threshold", np.nan):.3g}"""
    if attrs.get("max") is not None:
        title += f""" and < {attrs["max"]:.3g}"""
    if attrs.get("time") is not None:
        title += f""", time = {attrs["time"] * 1e3:.2f} ms"""
    ax.set_title(title)

    cbar = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.1)
    cbar.set_label(f"{field}{unit_label(units.get(field))}")

    return fig


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
    files = find_threshold_files(args["datapath"], args["fname"])
    if not files:
        sys.exit(f"""No threshold_*.pkl files in {args["datapath"]}""")

    # Loop over files, plot and save images
    for index, fpath in enumerate(files):

        # Load the data
        df = pd.read_pickle(fpath)
        # Print out the variables in the dataset
        if index == 0 and args["verbose"]:
            print(f"The variables contained in this file are: {list(df.columns)}")

        # Color by the thresholded field unless another is asked for
        field = args["field"] or df.attrs.get("field")
        if field not in df.columns:
            sys.exit(f"{field} not in {list(df.columns)}")

        if df.empty:
            print(f"Skipping {fpath}, it has no cells.")
            continue

        fig = plot_threshold(df, field, args)

        fbase = os.path.splitext(os.path.basename(fpath))[0]
        imgname = os.path.join(imgpath, f"{fbase}_{field}_3d.png")
        fig.savefig(imgname, dpi=args["dpi"], bbox_inches="tight")
        plt.close(fig)
        print(f"Saved {imgname}")


if __name__ == "__main__":
    main()
