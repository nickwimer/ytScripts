"""Extracts iso-surfaces from plot files and saves."""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402


def get_args():
    """Parse command line arguments."""
    # Initialize the class for data extraction
    ytparse = ytargs.ytExtractArgs()
    # Add in the arguments for the extract isosurfaces
    ytparse.isosurface_args()
    # Return the parsed arguments
    return ytparse.parse_args()


def main():
    """Main function for extracting isosurfaces."""
    # Parse the input arguments
    args = get_args()

    # Create the output directory
    outpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata", "isosurfaces"))
    os.makedirs(outpath, exist_ok=True)

    # Load the plt files
    ts, _ = utils.load_dataseries(
        datapath=args.datapath,
        pname=args.pname,
    )

    # Loop over the plt files in the data directory
    for ds in ts:
        # Force periodicity for the yt surface extraction routines...
        ds.force_periodicity()
        # Get the updated attributes for the current plt file
        ds_attributes = utils.get_attributes(ds=ds)

        # Create box region the encompasses the domain
        dregion = ds.box(
            left_edge=ds_attributes["left_edge"],
            right_edge=ds_attributes["right_edge"],
        )

        # Create iso-surface
        surf = ds.surface(
            data_source=dregion,
            surface_field=args.field,
            field_value=args.value,
        )

        # Export the isosurfaces in specified format
        fname = f"isosurface_{args.field}_{args.value}_{ds.basename}"
        if args.format == "ply":
            surf.export_ply(
                os.path.join(outpath, f"{fname}.ply"),
                bounds=[(-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0)],
                no_ghost=True,
            )
        elif args.format == "obj":
            verts, samples = dregion.extract_isocontours(
                # verts = dregion.extract_isocontours(
                field=args.field,
                value=args.value,
                # filename=os.path.join(outpath, f"{fname}.obj"),
                rescale=False,
                sample_values=args.field,
            )
            print(verts)
            print(samples)
        else:
            sys.exit(f"Format {args.format} not in [ply, obj]")


if __name__ == "__main__":
    main()
