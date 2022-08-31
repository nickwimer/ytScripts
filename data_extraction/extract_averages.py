"""Extracts domain averaged quantities and saves for plotting."""
import argparse
import os
import sys

import numpy as np
import pandas as pd
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
        help="path to the plt files",
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
        "--fields",
        type=str,
        nargs="+",
        required=True,
        default=None,
        help="Name of the data fields to extract",
    )
    parser.add_argument(
        "--SI",
        action="store_true",
        help="flag to identify if this simulation is in SI units (defaults to CGS)",
    )
    parser.add_argument(
        "--name",
        type=str,
        required=False,
        default="test",
        help="name of the output data",
    )
    return parser.parse_args()


def main():

    # Parse the input arguments
    args = get_args()

    # Create the output directory
    outpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata", "averages"))
    os.makedirs(outpath, exist_ok=True)

    # Override the units if needed
    if args.SI:
        units_override = {
            "length_unit": (1.0, "m"),
            "time_unit": (1.0, "s"),
            "mass_unit": (1.0, "kg"),
            "velocity_unit": (1.0, "m/s"),
        }
    else:
        units_override = None

    # Load data files into dataset series
    ts, _ = utils.load_dataseries(
        datapath=args.datapath, pname=args.pname, units_override=units_override
    )

    base_attributes = utils.get_attributes(ds=ts[0])

    print(f"""The fields in this dataset are: {base_attributes["field_list"]}""")

    avg_data = []
    time = []
    # Loop over the dataseries
    for ds in ts:
        time.append(float(ds.current_time))

        # Get all the data with no modifications
        # data = ds.r
        data = ds.covering_grid(
            base_attributes["max_level"],
            left_edge=base_attributes["left_edge"],
            dims=base_attributes["resolution"],
        )

        # Loop over the specified variables
        tmp_data = {}
        for field in args.fields:
            # Extract data and remove units
            tmp_data[field] = np.mean(
                np.mean(np.mean(YTArray(data[("boxlib", field)], "")))
            )

        avg_data.append(tmp_data)

    # Convert into a pandas dataframe for storage
    df = pd.DataFrame(data={"time": time}, columns=["time"])

    # Loop over the dataframe and add the data
    for idx, cell in df.iterrows():
        for key, value in avg_data[idx].items():
            df.loc[idx, key] = value

    # Save the data for later
    df.to_pickle(os.path.join(outpath, f"{args.name}.pkl"))


if __name__ == "__main__":
    main()
