"""Load averages from npz and plot."""
import os
import sys

import matplotlib.pyplot as plt
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

    for field in args.fields:

        fig, ax = plt.subplots(1, 1, figsize=(fx, fy))

        for fname in args.fname:
            # Load the dataframe
            df = pd.read_pickle(os.path.join(args.datapath, f"{fname}.pkl"))
            df.plot(
                x="time",
                y=field,
                ax=ax,
                label=f"""{fname} {field}""",
                marker="*",
                kind="scatter",
            )
            ax.set_xlabel("time (s)")
            ax.set_ylabel(field)
            ax.set_title("Domain Average vs. Time")

        fig.savefig(
            os.path.join(imgpath, f"""average_{field}_{'_'.join(args.fname)}.png"""),
            dpi=args.dpi,
        )


if __name__ == "__main__":
    main()
