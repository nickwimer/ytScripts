"""Extracts slices from plot files and saves."""
import os
import sys

import numpy as np

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402


def get_args():
    """Parse command line arguments."""
    # Initialize the class for data extraction
    ytparse = ytargs.ytExtractArgs()
    # Add in the arguments for the extract slices
    ytparse.slice_args()
    # Return the parsed arguments
    return ytparse.parse_args()


def main():

    # Parse the input arguments
    args = get_args()

    # Create the output directory
    outpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata", "slices"))
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

    # Load the plt files
    ts, _ = utils.load_dataseries(
        datapath=args.datapath, pname=args.pname, units_override=units_override
    )

    # Load a sample plt file for simulation geometry information
    ds0 = ts[0]
    time = ds0.current_time
    dimensions = ds0.domain_dimensions
    left_edge = ds0.domain_left_edge
    right_edge = ds0.domain_right_edge
    max_level = ds0.max_level

    # Compute dx, dy, dz
    (dx, dy, dz) = (right_edge - left_edge) / dimensions

    # Create the slice array and find indices closest to value
    xslice = np.linspace(args.xmin, args.xmax, args.num_slices)

    index = 0
    # Loop over the plt files in the data directory
    for ds in ts:
        # Get the simulation time
        time = ds.current_time

        resolution = dimensions[1] * 2**max_level

        # for xind in xindices:
        for xloc in xslice:
            # Create slice and fixed resolution close to the location
            slc = ds.r[xloc, :, :]
            frb = slc.to_frb(width=ds.domain_width[1], resolution=resolution)

            # Extract the variable requested
            var_slice = frb[args.field]

            # Save the slice to the output directory
            np.savez(
                os.path.join(outpath, f"{args.field}_x{xloc:.4f}_{index}.npz"),
                time=time,
                fcoords=slc.fcoords,
                resolution=resolution,
                dimensions=dimensions,
                left_edge=left_edge,
                right_edge=right_edge,
                max_level=max_level,
                xloc=xloc,
                field=args.field,
                var_slice=var_slice,
            )

        index += 1


if __name__ == "__main__":
    main()
