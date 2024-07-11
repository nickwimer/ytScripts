"""Extracts slices from plot files and saves."""

import os
import sys

import numpy as np
import yt

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402


def get_parser():
    """Get the parser."""
    ytparse = ytargs.ytExtractArgs()
    # Add in the arguments for the extract slices
    ytparse.orientation_args()
    ytparse.slice_args()

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
        outpath = args["outpath"]
    else:
        outpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata/", "slices"))
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

    # Load the plt files
    ts, index_dict = utils.load_dataseries(
        datapath=args["datapath"], pname=args["pname"], units_override=units_override
    )

    # Create the slice array and find indices closest to value
    islice = np.linspace(args["min"], args["max"], args["num_slices"])

    # Loop over the plt files in the data directory
    yt.enable_parallelism()
    for ds in ts.piter(dynamic=True):

        if args["field"]:
            vis_field = args["field"]
        else:
            vis_field = None

        # Visualize the gradient field, if requested
        if args["gradient"]:
            vis_field = utils.get_gradient_field(ds, args["field"], args["gradient"])
        else:
            vis_field = args["field"]

        # Get updated attributes for current plt file
        ds_attributes = utils.get_attributes(ds=ds)

        # Set index according to dict
        index = index_dict[str(ds)]

        # for xind in xindices:
        for iloc in islice:
            # Do a grid offset if requested
            iloc += args["grid_offset"]
            # Create slice and fixed resolution close to the location
            if args["normal"] == "x":
                slc = ds.r[iloc, :, :]
                frb = slc.to_frb(
                    width=ds_attributes["width"][1],
                    height=ds_attributes["width"][2],
                    resolution=(
                        ds_attributes["resolution"][1],
                        ds_attributes["resolution"][2],
                    ),
                )
            elif args["normal"] == "y":
                slc = ds.r[:, iloc, :]
                frb = slc.to_frb(
                    width=ds_attributes["width"][0],
                    height=ds_attributes["width"][2],
                    resolution=(
                        ds_attributes["resolution"][0],
                        ds_attributes["resolution"][2],
                    ),
                )
            elif args["normal"] == "z":
                slc = ds.r[:, :, iloc]
                frb = slc.to_frb(
                    width=ds_attributes["width"][0],
                    height=ds_attributes["width"][1],
                    resolution=(
                        ds_attributes["resolution"][0],
                        ds_attributes["resolution"][1],
                    ),
                )
            else:
                raise ValueError(f"""Normal {args["normal"]} not in: [x, y, z]""")

            # Extract the variable requested
            slices = {}
            slices[vis_field] = frb[vis_field]
            fields = vis_field

            # Save the slice to the output directory
            np.savez(
                os.path.join(
                    outpath, f"""{vis_field}_{args["normal"]}{iloc:.4f}_{index}.npz"""
                ),
                fcoords=slc.fcoords,
                normal=args["normal"],
                iloc=iloc,
                fields=fields,
                slices=slices,
                ds_attributes=ds_attributes,
            )


if __name__ == "__main__":
    main()
