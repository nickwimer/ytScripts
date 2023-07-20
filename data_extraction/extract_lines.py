"""Extracts lines from plot files and saves."""
import os
import sys
import time

import numpy as np
import pandas as pd
import yt

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402


def get_args():
    """Parse command line arguments."""
    # Initialize the class for data extraction
    ytparse = ytargs.ytExtractArgs()
    # Add in the arguments for the extract lines
    ytparse.orientation_args()
    ytparse.line_args()
    # Return the parsed arguments
    return ytparse.parse_args()


def main():

    # Parse the input arguments
    args = get_args()

    # Create the output directory
    if args.outpath:
        outpath = args.outpath
    else:
        outpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata/", "lines"))
    os.makedirs(outpath, exist_ok=True)

    # Override the units if needed
    if args.SI:
        units_override = {
            "length_unit": (1.0, "m"),
            "time_unit": (1.0, "s"),
            "mass_unit": (1.0, "kg"),
            "velocity_unit": (1.0, "m/s"),
        }
        eb_var_name = "volFrac"
    else:
        units_override = None
        eb_var_name = "vfrac"

    # start timer
    if yt.is_root():
        start_time = time.time()

    # Load the plt files
    ts, index_dict = utils.load_dataseries(
        datapath=args.datapath, pname=args.pname, units_override=units_override
    )

    base_attributes = utils.get_attributes(ds=ts[0])

    if args.verbose:
        print(f"""The fields in this dataset are: {base_attributes["field_list"]}""")
        print(
            f"""The derived fields in this dataset are: """
            f"""{base_attributes["derived_field_list"]}"""
        )

    # define normal dict
    norm_dict = {"x": 0, "y": 1, "z": 2}

    # Loop over the plt files in the data directory
    if not args.no_mpi:
        yt.enable_parallelism()
    data_dict = {}
    for sto, ds in ts.piter(storage=data_dict, dynamic=True):
        sto.result_id = float(ds.current_time)

        all_data = ds.all_data()

        # Filter out the EB regions
        if args.rm_eb:
            data = ds.cut_region(all_data, [f"obj[('boxlib', '{eb_var_name}')] > 0.5"])
        else:
            data = all_data

        # Take a line of the data
        tmp_ray = ds.ortho_ray(
            axis=norm_dict[args.normal], coords=args.coords, data_source=data
        )

        # Store the data for each plot file
        tmp_data = {}
        tmp_data[args.field] = np.array(tmp_ray[args.field])
        tmp_data[args.normal] = np.array(tmp_ray[args.normal])
        sto.result = tmp_data

    if yt.is_root():
        key_list = list(data_dict.keys())

        # initialize dataframe
        df = pd.DataFrame(columns=key_list, index=data_dict[key_list[0]][args.normal])

        # Loop over time and fill dataframe
        for itime in range(len(key_list)):
            df[key_list[itime]] = data_dict[key_list[itime]][args.field]

        # Make sure the date is properly sorted
        df = df.sort_index()

        # Save the data for later
        df.to_pickle(os.path.join(outpath, f"{args.name}.pkl"))

        # print total time
        print(f"Total elapsed time = {time.time() - start_time} seconds")


if __name__ == "__main__":
    main()
