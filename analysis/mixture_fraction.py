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
    # Initialize the class for data analysis
    ytparse = ytargs.ytAnalysisArgs()
    # Add in the arguments for the mixture fraction
    ytparse.mixture_fraction()
    # Parse the args
    args = ytparse.parse_args()

    # Return the parsed arguments
    return args


def _mixture_fraction(field, data):
    return 1 - (data[("boxlib", "Y(N2)")]) / 0.77


def main():

    # Parse the input arguments
    args = get_args()

    # Create the output directory
    if args.outpath:
        outpath = args.outpath
    else:
        outpath = os.path.abspath(
            os.path.join(sys.argv[0], "../../outdata", "analysis")
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

    # start timer
    if yt.is_root():
        start_time = time.time()

    # Load data files into dataset series
    ts, _ = utils.load_dataseries(
        datapath=args.datapath,
        pname=args.pname,
        units_override=units_override,
        nprocs=args.nprocs,
        nskip=args.nskip,
    )

    base_attributes = utils.get_attributes(ds=ts[0])

    if args.verbose:
        print(f"""The fields in this dataset are: {base_attributes["field_list"]}""")
        print(
            f"""The derived fields in this dataset are: """
            f"""{base_attributes["derived_field_list"]}"""
        )

    # (
    #     elem_mass_frac_all,
    #     atomic_mass_dict,
    #     spec_fields,
    # ) = utils.compute_elem_mass_fraction(base_attributes)

    # elem_mass_frac_oxy, _, _ = utils.compute_elem_mass_fraction(
    #     base_attributes, keys=["H2", "O2", "CH4"]
    # )

    # elem_mass_frac_fuel, _, _ = utils.compute_elem_mass_fraction(
    #     base_attributes, keys=["NC12H26"]
    # )

    # Define mixture fraction function with access to all defined variables
    # def _mixture_fraction(field, data):

    # tot_elem_mfrac = {"C": 0, "H": 0, "O": 0, "N": 0}
    # for fname in spec_fields:
    #     cut_name = fname[1][2:-1]
    #     if cut_name[0:2] == "NC":
    #         cut_name = cut_name[1:]
    #     # print(fname)
    #     tot_elem_mfrac["C"] += (
    #         data[fname]
    #         / data[("boxlib", "density")]
    #         * elem_mass_frac_all[cut_name]["C"]
    #     )
    #     tot_elem_mfrac["H"] += (
    #         data[fname]
    #         / data[("boxlib", "density")]
    #         * elem_mass_frac_all[cut_name]["H"]
    #     )
    #     tot_elem_mfrac["O"] += (
    #         data[fname]
    #         / data[("boxlib", "density")]
    #         * elem_mass_frac_all[cut_name]["O"]
    #     )

    # mix_frac = (
    #     2 * tot_elem_mfrac["C"] / atomic_mass_dict["C"]
    #     + 0.5 * tot_elem_mfrac["H"] / atomic_mass_dict["H"]
    #     + (-tot_elem_mfrac["O"]) / atomic_mass_dict[")"]
    # ) / ()
    # exit()

    # mix_frac = (2*elem_mass_frac_all[""])

    # # compute elemental mass fraction of H, C, O
    # print(data[("boxlib", "Y(H2O)")])
    # print(ds)

    # create mix frac bins
    mix_frac_bins = np.linspace(0, 1, 11)

    # Loop over the dataseries
    if not args.no_mpi:
        yt.enable_parallelism()
    data_dict = {}
    for sto, ds in ts.piter(storage=data_dict, dynamic=True):
        sto.result_id = float(ds.current_time)

        ds.add_field(
            ("gas", "mix_frac"),
            function=_mixture_fraction,
            units="",
            take_log=False,
            display_name="mixture fraction",
            sampling_type="cell",
        )

        all_data = ds.all_data()

        # Filter out the EB regions
        if args.rm_eb:
            data = ds.cut_region(all_data, ["obj[('boxlib', 'vfrac')] > 0.5"])
        else:
            data = all_data

        # data = data.get_data(fields=["Temp", "mix_frac", ("boxlib", "cell_volume")])

        tmp_data = {}
        # temp_bins = []
        for i in range(len(mix_frac_bins) - 1):
            print(mix_frac_bins[i], mix_frac_bins[i + 1])
            di = data.include_inside(
                ("gas", "mix_frac"), mix_frac_bins[i], mix_frac_bins[i + 1]
            )
            # temp_bins.append(di.mean(("boxlib", "Temp"), weight=("boxlib", "cell_volume")))
            tmp_data[f"temp_bin_{i}"] = di.mean(
                ("boxlib", "Temp"), weight=("boxlib", "cell_volume")
            )

        # tmp_data["temp_bins"] = temp_bins
        # tmp_data["mix_frac_bins"] = mix_frac_bins

        sto.result = tmp_data

    print(data_dict)

    if yt.is_root():
        # Convert into a pandas dataframe for storage
        # df = pd.DataFrame(data={"time": time}, columns=["time"])
        df = pd.DataFrame(data={"time": data_dict.keys()})
        print(df)
        # df["temp_bins"] = df["temp_bins"].astype(object)

        # Loop over the dataframe and add the data
        for idx, cell in df.iterrows():
            for key, value in data_dict[cell["time"]].items():
                print(key, value)
                df.loc[idx, key] = value

        print(df)
        # Save the data for later
        df.to_pickle(os.path.join(outpath, f"{args.name}.pkl"))

        # print total time
        print(f"Total elapsed time = {time.time() - start_time} seconds")


if __name__ == "__main__":
    main()
