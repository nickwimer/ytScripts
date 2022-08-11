"""Extracts slices from plot files and saves."""
import argparse
import os

import numpy as np
import yt

if __name__ == "__main__":

    # Parse the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--datapath",
        type=str,
        required=True,
        help="path to the plot files",
    )
    parser.add_argument(
        "-r",
        "--res",
        type=int,
        required=False,
        help="resolution at which we extract the data slices",
    )
    parser.add_argument(
        "--field",
        type=str,
        required=True,
        help="variable name to extract",
    )
    parser.add_argument(
        "--xmin",
        type=float,
        required=True,
        help="index of the first slice to extract in the x direction",
    )
    parser.add_argument(
        "--xmax",
        type=float,
        required=True,
        help="index of the last slice to extract in the x direction",
    )
    parser.add_argument(
        "--num_slices",
        type=int,
        required=True,
        help="number of slices to extract in x direction",
    )
    parser.add_argument(
        "--LM",
        action="store_true",
        help="flag to identify if this is a low Mach simulation",
    )
    args = parser.parse_args()

    # Get the current directory
    cwd = os.getcwd()

    # Create the output directory
    outpath = os.path.join(cwd, "outdata")
    if not os.path.exists(outpath):
        os.makedirs(outpath)

    # Override the units if needed
    if args.LM:
        units_override = {
            "length_unit": (1.0, "m"),
            "time_unit": (1.0, "s"),
            "mass_unit": (1.0, "kg"),
            "velocity_unit": (1.0, "m/s"),
        }
    else:
        units_override = None

    # Load the plt files
    ts = yt.load(
        os.path.join(args.datapath, "plt?????"),
        units_override=units_override,
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
