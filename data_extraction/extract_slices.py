"""Extracts slices from plot files and saves."""

import os
import sys

import numpy as np

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
    # Parse the command line, merged with the input file if one is given
    args = parser.get_args()

    # Return the parsed arguments as a dict
    return args


def cut_plane(ds, ds_attributes, normal, across, up_vec, distance):
    """Cut the plane normal . r = distance and make a fixed resolution image of it.

    The image covers the part of the plane inside the domain, with one pixel per
    finest cell, ``across`` to the right and ``up_vec`` up. Returns the cutting
    plane, the image and what places it: the unit normal, across and up vectors,
    the image center and its bounds (across_min, across_max, up_min, up_max) as
    positions along across and up, in code_length. Those positions are the same for
    every slice with this normal, so the slices line up when plotted.
    """
    left = utils.code_length_values(ds, ds_attributes["left_edge"])
    right = utils.code_length_values(ds, ds_attributes["right_edge"])
    center = utils.plane_center(left, right, normal, distance)
    (across_lo, across_hi), (up_lo, up_hi) = utils.plane_window(
        left, right, normal, center, across, up_vec
    )
    # Center the image on the part of the plane inside the domain
    center = (
        center + (across_lo + across_hi) / 2.0 * across + (up_lo + up_hi) / 2.0 * up_vec
    )
    width, height = across_hi - across_lo, up_hi - up_lo

    finest = utils.code_length_values(ds, ds_attributes["width"]) / np.asarray(
        ds_attributes["resolution"], dtype=np.float64
    )
    resolution = (
        utils.pixels_along(across, finest, width),
        utils.pixels_along(up_vec, finest, height),
    )

    slc = ds.cutting(normal, center, north_vector=up_vec)
    frb = slc.to_frb(
        width=ds.quan(width, "code_length"),
        height=ds.quan(height, "code_length"),
        resolution=resolution,
    )
    plane = {
        "normal_vector": normal,
        "across": across,
        "up": up_vec,
        "center": center,
        "bounds": np.array(
            [
                center @ across - width / 2,
                center @ across + width / 2,
                center @ up_vec - height / 2,
                center @ up_vec + height / 2,
            ]
        ),
    }
    return slc, frb, plane


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
    islice = np.linspace(
        float(args["min"]), float(args["max"]), int(args["num_slices"])
    )

    # A diagonal normal gives cutting planes, at a distance along the unit normal
    oblique = not utils.is_axis_normal(args["normal"])
    if oblique:
        normal, across, up_vec = utils.slice_basis(args["normal"])
        labels = np.array(
            [utils.direction_label(across), utils.direction_label(up_vec)]
        )

        # Every plane must cut through the domain; check before reading any plotfile
        ds0 = ts[0]
        left = utils.code_length_values(ds0, ds0.domain_left_edge)
        right = utils.code_length_values(ds0, ds0.domain_right_edge)
        try:
            for distance in islice + args["grid_offset"]:
                utils.plane_center(left, right, normal, distance)
        except ValueError as err:
            parser.get_parser().error(f"--min/--max: {err}")

    # Loop over the plt files in the data directory
    # Share the plotfiles over MPI only when launched with mpirun or srun
    utils.enable_parallelism(no_mpi=args["no_mpi"])
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
            plane = {}
            if oblique:
                slc, frb, plane = cut_plane(
                    ds, ds_attributes, normal, across, up_vec, iloc
                )
                plane["labels"] = labels
            elif args["normal"] == "x":
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
                **plane,
            )


if __name__ == "__main__":
    main()
