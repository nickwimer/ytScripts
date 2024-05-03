"""Extracts grid information at each level and saves to file."""

import os
import sys

import pandas as pd
import yt

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402


def get_args():
    """Parse command line arguments."""
    # Initialize the class for data extraction
    ytparse = ytargs.ytExtractArgs()
    # Add in the arguments for the grid info extraction
    ytparse.grid_args()

    # Get the initial set of arguments
    init_args = ytparse.parse_args()

    # Override the command-line arguments with the input file
    if init_args.ifile:
        args = ytparse.override_args(init_args, init_args.ifile)
    else:
        args = vars(init_args)

    # Return the parsed arguments as a dict
    return args


def main():
    """Main function for grid info extraction."""

    # Parse the input arguments
    args = get_args()

    # Create the output directory
    if args["outpath"]:
        outpath = args["outpath"]
    else:
        outpath = os.path.abspath(
            os.path.join(sys.argv[0], "../../outdata", "grid_info")
        )
    os.makedirs(outpath, exist_ok=True)

    # Override the units if needed
    if args["SI"]:
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
        datapath=args["datapath"], pname=args["pname"], units_override=units_override
    )

    base_attributes = utils.get_attributes(ds=ts[0])

    if args["verbose"]:
        print(f"""The fields in this dataset are: {base_attributes["field_list"]}""")

    # Loop over the dataseries
    yt.enable_parallelism()
    data_dict = {}
    for sto, ds in ts.piter(storage=data_dict, dynamic=True):
        sto.result_id = float(ds.current_time)

        level_data = ds.index.level_stats[0 : ds.index.max_level + 1]

        tmp_df = pd.DataFrame(
            data=level_data,
            index=level_data["level"],
            columns=["numgrids", "numcells"],
        )

        sto.result = tmp_df

    if yt.is_root():

        # Convert into a pandas dataframe for storage
        df = pd.DataFrame({"time": data_dict.keys(), "grid_data": data_dict.values()})

        # Sort the dataframe by time
        df.sort_values(by="time", inplace=True, ignore_index=True)

        # Add some metadata
        df.attrs["base_attributes"] = base_attributes

        # Save the data for later
        df.to_pickle(os.path.join(outpath, f"""{args["name"]}.pkl"""))


if __name__ == "__main__":
    main()
