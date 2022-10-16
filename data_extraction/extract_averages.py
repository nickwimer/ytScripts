"""Extracts domain averaged quantities and saves for plotting."""
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
    # Add in the arguments for the extract averages
    ytparse.average_args()
    # Return the parsed arguments
    return ytparse.parse_args()


def main():

    # Parse the input arguments
    args = get_args()

    # Create the output directory
    if args.outpath:
        outpath = args.outpath
    else:
        outpath = os.path.abspath(
            os.path.join(sys.argv[0], "../../outdata", "averages")
        )
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

    if args.verbose:
        print(f"""The fields in this dataset are: {base_attributes["field_list"]}""")

    # Loop over the dataseries
    yt.enable_parallelism()
    data_dict = {}
    for sto, ds in ts.piter(storage=data_dict, dynamic=True):
        sto.result_id = float(ds.current_time)

        # Get all the data with no modifications
        data = ds.all_data()
        # Loop over the specified variables
        tmp_data = {}
        for field in args.fields:
            tmp_data[field] = data.mean(
                ("boxlib", field), weight=("boxlib", "cell_volume")
            )

        sto.result = tmp_data

    if yt.is_root():
        # Convert into a pandas dataframe for storage
        # df = pd.DataFrame(data={"time": time}, columns=["time"])
        df = pd.DataFrame(data={"time": data_dict.keys()})
        # df = pd.DataFrame

        # Loop over the dataframe and add the data
        for idx, cell in df.iterrows():
            for key, value in data_dict[cell["time"]].items():
                df.loc[idx, key] = value

        # Save the data for later
        df.to_pickle(os.path.join(outpath, f"{args.name}.pkl"))


if __name__ == "__main__":
    main()
