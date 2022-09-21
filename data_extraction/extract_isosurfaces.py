"""Extracts iso-surfaces from plot files and saves."""
import os
import sys

import h5py
import numpy as np

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


def write_xdmf(fbase, field, ftype, value, time, conn_shape, coord_shape, field_shape):
    """Write the XDMF wrapper based on the hdf5 data."""
    # Create the XDMF file for writing
    xdmf_file = open(f"{fbase}.xmf", "w")
    # Form the header of the xdmf file
    xdmf_file.write(
        """<?xml version="1.0"?>\n"""
        """<Xdmf Version="3.0" xmlns:xi="http://www.w3.org/2001/XInclude">\n"""
    )

    # Form the Domain block
    xdmf_file.write("\t<Domain>\n")

    # Form the Grid block
    xdmf_file.write(
        f"""\t\t<Grid Name="isoSurface" GridType="Uniform">\n"""
        f"""\t\t<Information Name="Variable" Value="{field}"/>\n"""
        f"""\t\t<Information Name="IsoValue" Value="{value}"/>\n"""
        f"""\t\t<Time Value="{time}"/>\n"""
    )

    # Form the Topology block
    xdmf_file.write(
        f"""\t\t\t<Topology TopologyType="Triangle" NumberOfElements="""
        f""""{conn_shape[0]} {conn_shape[1]}">\n"""
        f"""\t\t\t\t<DataItem Name="Conn" Format="HDF" DataType="Int" """
        f"""Precision="4" Dimensions="{conn_shape[0]} {conn_shape[1]}">\n"""
        f"""\t\t\t\t\t{fbase}.hdf5:/Conn\n"""
        f"""\t\t\t\t</DataItem>\n"""
        f"""\t\t\t</Topology>\n"""
    )

    # Form the Geometry block
    xdmf_file.write(
        f"""\t\t\t<Geometry GeometryType="XYZ" NumberOfElements="""
        f""""{coord_shape[0]} {coord_shape[1]}">\n"""
        f"""\t\t\t\t<DataItem Name="Coord" Format="HDF" DataType="Float" """
        f"""Precision="8" Dimensions="{coord_shape[0]} {coord_shape[1]}">\n"""
        f"""\t\t\t\t\t{fbase}.hdf5:/Coord\n"""
        f"""\t\t\t\t</DataItem>\n"""
        f"""\t\t\t</Geometry>\n"""
    )

    # Form the Attribute block
    xdmf_file.write(
        f"""\t\t\t<Attribute Name="{field}" AttributeType="{ftype}" Center="Cell">\n"""
        f"""\t\t\t\t<DataItem Format="HDF" DataType="Float" Precision="8" """
        f"""Dimensions="{field_shape[0]}">\n"""
        f"""\t\t\t\t\t{fbase}.hdf5:/{field}\n"""
        f"""\t\t\t\t</DataItem>\n"""
        f"""\t\t\t</Attribute>\n"""
    )

    # Ending of the Grid block
    xdmf_file.write("\t\t</Grid>\n")

    # Ending of the Domain block
    xdmf_file.write("\t</Domain>\n")

    # Ending of the XDFM file
    xdmf_file.write("</Xdmf>")

    xdmf_file.close()


def write_hdf5(verts, samples, field, fname):
    """Write the HDF5 file based on the extracted isosurface."""
    # Get the shape of the vertices for the connection array
    len_verts, dep_verts = np.shape(verts)

    # Make triangle connection array taking the vertices in groups of three
    tri_array = np.arange(0, len_verts, 1)
    tri_array = tri_array.reshape((-1, 3))

    # Write the hdf5 file
    with h5py.File(fname, "w") as f:
        f.create_dataset("Conn", data=tri_array, dtype=np.int32)
        f.create_dataset("Coord", data=verts, dtype=np.float64)
        f.create_dataset(field, data=samples, dtype=np.float64)

    return np.shape(tri_array), np.shape(verts), np.shape(samples)


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
            dregion.extract_isocontours(
                field=args.field,
                value=args.value,
                filename=os.path.join(outpath, f"{fname}.obj"),
                rescale=False,
            )
        elif args.format in ["hdf5", "xdmf"]:
            # xdmf or hdf5 will write the hdf5 file and the xdmf wrapper file
            verts, samples = dregion.extract_isocontours(
                field=args.field,
                value=args.value,
                rescale=False,
                sample_values=args.field,
            )

            conn_shape, coord_shape, field_shape = write_hdf5(
                verts=verts,
                samples=np.array(samples),
                field=args.field,
                fname=os.path.join(outpath, f"{fname}.hdf5"),
            )

            write_xdmf(
                fbase=os.path.join(outpath, fname),
                field=args.field,
                ftype="Scalar",
                value=args.value,
                time=ds_attributes["time"],
                conn_shape=conn_shape,
                coord_shape=coord_shape,
                field_shape=field_shape,
            )

        else:
            sys.exit(f"Format {args.format} not in [ply, obj, hdf5, xdmf]")


if __name__ == "__main__":
    main()
