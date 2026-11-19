"""Extracts axis-aligned lines of data from plot files and saves them."""

import os
import sys
import time

import numpy as np
import pandas as pd
import yt

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402


def get_parser():
    """Get the parser."""
    ytparse = ytargs.ytExtractArgs()
    # Add in the arguments for the extract lines
    ytparse.line_args()

    return ytparse


def get_base_parser():
    """Get the base level parser primarily for documentation."""
    return get_parser().get_parser()


def get_args(parser, cli_args=None):
    """Get the arguments from the parser (cli_args defaults to sys.argv)."""
    # Parse the command line, merged with the input file if one is given
    args = parser.get_args(cli_args)

    # The line is fixed by its position in the other two directions
    if not isinstance(args["coords"], list) or len(args["coords"]) != 2:
        parser.get_parser().error("--coords needs exactly two values")

    # Return the parsed arguments as a dict
    return args


def lines_to_dataframe(lines, normal):
    """Combine the line from each time into one table.

    ``lines`` maps each time to ``(positions, values, ...)``. With AMR the cells
    along the line can change from one time to the next, so each line keeps its own
    positions. The table is indexed by every position seen at any time, sorted, with
    one column per time and NaN where that time has no cell at that position.
    """
    columns = {}
    for itime in sorted(lines):
        positions, values = lines[itime][:2]
        line = pd.Series(np.asarray(values), index=np.asarray(positions))
        # Guard against repeated positions, which would break the alignment
        columns[itime] = line.groupby(level=0).mean()

    df = pd.DataFrame(columns).sort_index()
    df.index.name = normal
    df.columns.name = "time"

    return df


def main():
    """Extract a line of data along an axis for each plot file."""
    # Parse the input arguments
    parser = get_parser()
    args = get_args(parser)

    # Create the output directory
    if args["outpath"]:
        outpath = args["outpath"]
    else:
        outpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata", "lines"))
    os.makedirs(outpath, exist_ok=True)

    # Override the units if needed
    if args["SI"]:
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

    # Load data files into dataset series
    ts, _ = utils.load_dataseries(
        datapath=args["datapath"],
        pname=args["pname"],
        units_override=units_override,
        nprocs=args["nprocs"],
        nskip=args["nskip"],
    )

    base_attributes = utils.get_attributes(ds=ts[0])

    if args["verbose"]:
        print(f"""The fields in this dataset are: {base_attributes["field_list"]}""")
        print(
            f"""The derived fields in this dataset are: """
            f"""{base_attributes["derived_field_list"]}"""
        )

    axis = {"x": 0, "y": 1, "z": 2}[args["normal"]]

    # Loop over the dataseries
    # Share the plotfiles over MPI only when launched with mpirun or srun
    utils.enable_parallelism(no_mpi=args["no_mpi"])
    lines = {}
    for sto, ds in ts.piter(storage=lines, dynamic=True):
        sto.result_id = float(ds.current_time)

        # Filter out the EB regions
        if args["rm_eb"]:
            data_source = ds.cut_region(
                ds.all_data(), [f"obj[('boxlib', '{eb_var_name}')] > 0.5"]
            )
        else:
            data_source = None

        # Take a line of the data through the finest cells along the axis
        ray = ds.ortho_ray(axis=axis, coords=args["coords"], data_source=data_source)
        positions = ray[args["normal"]]
        values = ray[args["field"]]

        # Send the units with the data, since under MPI the root does no work
        units = {"position": str(positions.units), "field": str(values.units)}
        sto.result = (np.array(positions), np.array(values), units)

    if yt.is_root():
        df = lines_to_dataframe(lines, args["normal"])

        # Keep what the table holds with the data
        df.attrs["field"] = args["field"]
        df.attrs["coords"] = args["coords"]
        df.attrs["units"] = next(iter(lines.values()))[2]

        # Save the data for later
        df.to_pickle(os.path.join(outpath, f"""{args["name"]}.pkl"""))

        # print total time
        print(f"Total elapsed time = {time.time() - start_time} seconds")


if __name__ == "__main__":
    main()
