"""Extracts iso-surfaces from plot files and saves."""
import os
import sys
import time

import h5py
import numpy as np
import yt
from skimage import measure
from yt.utilities.parallel_tools.parallel_analysis_interface import communication_system

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402

# from yt import enable_parallelism, is_root


def get_args():
    """Parse command line arguments."""
    # Initialize the class for data extraction
    ytparse = ytargs.ytExtractArgs()
    # Add in the arguments for the extract isosurfaces
    ytparse.isosurface_args()
    # Return the parsed arguments
    return ytparse.parse_args()


def write_xdmf(
    fbase, field, ftype, ctype, value, time, conn_shape, coord_shape, field_shape
):
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
        f"""\t\t\t<Attribute Name="{field}" AttributeType="{ftype}" """
        f"""Center="{ctype}">\n"""
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


def write_hdf5(verts, samples, faces, field, fname):
    """Write the HDF5 file based on the extracted isosurface."""
    with h5py.File(fname, "w") as f:
        # f.create_dataset("Conn", data=tri_array, dtype=np.int32)
        f.create_dataset("Conn", data=faces.astype(np.int32), dtype=np.int32)
        f.create_dataset("Coord", data=verts, dtype=np.float64)
        f.create_dataset(field, data=samples, dtype=np.float64)

    return np.shape(faces), np.shape(verts), np.shape(samples)


def main():
    """Main function for extracting isosurfaces."""
    # Parse the input arguments
    args = get_args()

    comm = communication_system.communicators[-1]

    # Create the output directory
    if comm.rank == 0:
        outpath = os.path.abspath(
            os.path.join(sys.argv[0], "../../outdata", "isosurfaces")
        )
        os.makedirs(outpath, exist_ok=True)

    # # Load the plt files
    ts, _ = utils.load_dataseries(
        datapath=args.datapath,
        pname=args.pname,
    )
    # ds = yt.load(os.path.join(args.datapath, "plt10000"), parallel=False)

    if comm.rank == 0:
        start_time = time.time()

    # Loop over the plt files in the data directory
    for ds in ts.piter():

        # Force periodicity for the yt surface extraction routines...
        ds.force_periodicity()

        # Get the updated attributes for the current plt file
        ds_attributes = utils.get_attributes(ds=ds)

        # Create box region the encompasses the domain
        # dregion = ds.box(
        # #     # left_edge=ds_attributes["left_edge"],
        # #     # right_edge=ds_attributes["right_edge"],
        #     left_edge=ds.domain_left_edge,
        #     right_edge=ds.domain_right_edge,
        # )
        dregion = ds.all_data()
        # dregion = ds.smoothed_covering_grid(
        #     level=ds_attributes["max_level"],
        #     left_edge=ds_attributes["left_edge"],
        #     dims=ds_attributes["resolution"],
        # )

        # Export the isosurfaces in specified format
        fname = f"isosurface_{args.field}_{args.value}_{ds.basename}"
        if args.yt:
            fname += "_yt"

        if args.format == "ply":
            # Create iso-surface
            surf = ds.surface(
                data_source=dregion,
                surface_field=args.field,
                field_value=args.value,
            )

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

            if args.yt:
                verts, samples = dregion.extract_isocontours(
                    field=args.field,
                    value=args.value,
                    rescale=False,
                    sample_values=args.field,
                )

                verts_np = np.array(verts)
                # Get the shape of the vertices for the connection array
                len_verts, dep_verts = np.shape(verts)

                # Make faces connection array taking the vertices in groups of three
                faces_np = np.arange(0, len_verts, 1)
                faces_np = faces_np.reshape((-1, dep_verts))
                samples_np = np.array(samples)

            else:

                # dregion = dregion.retrieve_ghost_zones(
                #     n_zones=4,
                #     fields=args.field,
                #     all_levels=True,
                #     smoothed=False,
                # )

                verts_np = np.empty((0, 3))
                faces_np = np.empty((0, 3))
                samples_np = np.empty((0))

                for g in dregion.index.grids:

                    # g = g.retrieve_ghost_zones(
                    #     n_zones=1, fields=args.field, all_levels=False, smoothed=False
                    # )
                    # Get the physical cell spacing of the grid
                    dx = np.array(g[("boxlib", "dx")][0, 0, 0])
                    dy = np.array(g[("boxlib", "dy")][0, 0, 0])
                    dz = np.array(g[("boxlib", "dz")][0, 0, 0])

                    try:
                        verts, faces, normals, values = measure.marching_cubes(
                            volume=g[args.field],
                            level=args.value,
                            # allow_degenerate=False,
                            allow_degenerate=True,
                            step_size=1,
                            gradient_direction="ascent",
                            spacing=(dx, dy, dz),
                            method="lewiner",
                            # mask=g.child_mask,
                        )

                        # offset the physical location
                        verts += np.array(g.fcoords.min(axis=0))

                        # offset the face indices by the current length of the array
                        len_verts, _ = np.shape(verts_np)
                        faces += len_verts

                        verts_np = np.append(verts_np, verts, axis=0)
                        faces_np = np.append(faces_np, faces, axis=0)
                        samples_np = np.append(samples_np, values, axis=0)

                    except ValueError:
                        # Skip the regions that do not have values for the isosurface
                        pass

                    # except RuntimeError:
                    # Skip the regions that
                    # pass

                    # clear the data to reduce memory constraints
                    g.clear_data()

                # Explicitly cast the arrays as necessary types
                verts_np = verts_np.astype(np.float64)
                faces_np = faces_np.astype(np.int32)
                samples_np = samples_np.astype(np.float64)

            # Write out the hdf5 and the xdmf file
            if comm.rank == 0:
                conn_shape, coord_shape, field_shape = write_hdf5(
                    verts=verts_np,
                    samples=samples_np,
                    faces=faces_np,
                    field=args.field,
                    fname=os.path.join(outpath, f"{fname}.hdf5"),
                )

                write_xdmf(
                    fbase=os.path.join(outpath, fname),
                    field=args.field,
                    ftype="Scalar",
                    ctype="Node" if not args.yt else "Cell",
                    value=args.value,
                    time=ds_attributes["time"],
                    conn_shape=conn_shape,
                    coord_shape=coord_shape,
                    field_shape=field_shape,
                )

        else:
            sys.exit(f"Format {args.format} not in [ply, obj, hdf5, xdmf]")

    if yt.is_root():
        print(f"Elapsed time = {time.time() - start_time} seconds.")


if __name__ == "__main__":
    main()
