"""Extracts iso-surfaces from plot files and saves."""
import os
import sys
import time

import h5py
import numpy as np
from mpi4py import MPI
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes

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


def write_xdmf(
    fbase, fhdf5, field, ftype, ctype, value, time, conn_shape, coord_shape, field_shape
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
        f"""\t\t\t\t\t{fhdf5}.hdf5:/Conn\n"""
        f"""\t\t\t\t</DataItem>\n"""
        f"""\t\t\t</Topology>\n"""
    )

    # Form the Geometry block
    xdmf_file.write(
        f"""\t\t\t<Geometry GeometryType="XYZ" NumberOfElements="""
        f""""{coord_shape[0]} {coord_shape[1]}">\n"""
        f"""\t\t\t\t<DataItem Name="Coord" Format="HDF" DataType="Float" """
        f"""Precision="8" Dimensions="{coord_shape[0]} {coord_shape[1]}">\n"""
        f"""\t\t\t\t\t{fhdf5}.hdf5:/Coord\n"""
        f"""\t\t\t\t</DataItem>\n"""
        f"""\t\t\t</Geometry>\n"""
    )

    # Form the Attribute block
    xdmf_file.write(
        f"""\t\t\t<Attribute Name="{field}" AttributeType="{ftype}" """
        f"""Center="{ctype}">\n"""
        f"""\t\t\t\t<DataItem Format="HDF" DataType="Float" Precision="8" """
        f"""Dimensions="{field_shape[0]}">\n"""
        f"""\t\t\t\t\t{fhdf5}.hdf5:/{field}\n"""
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
        f.create_dataset("Conn", data=faces.astype(np.int32), dtype=np.int32)
        f.create_dataset("Coord", data=verts, dtype=np.float64)
        f.create_dataset(field, data=samples, dtype=np.float64)

    return np.shape(faces), np.shape(verts), np.shape(samples)


def do_isosurface_extraction(
    dregion,
    ds_attributes,
    outformat,
    field,
    value,
    outpath,
    fname,
    comm,
    rank,
    size,
    do_ghost=False,
    do_yt=False,
    single_level=False,
    smooth=None,
    ds=None,
    iso_edge=None,
):
    """Do the isosurface extraction according to the input parameters."""
    if outformat == "ply":
        # Create iso-surface
        surf = ds.surface(
            data_source=dregion,
            surface_field=field,
            field_value=value,
        )

        surf.export_ply(
            os.path.join(outpath, f"{fname}.ply"),
            bounds=[(-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0)],
            no_ghost=True,
        )
    elif outformat == "obj":
        dregion.extract_isocontours(
            field=field,
            value=value,
            filename=os.path.join(outpath, f"{fname}.obj"),
            rescale=False,
        )
    elif outformat in ["hdf5", "xdmf"]:
        # xdmf or hdf5 will write the hdf5 file and the xdmf wrapper file

        if do_yt:
            verts, samples = dregion.extract_isocontours(
                field=field,
                value=value,
                rescale=False,
                sample_values=field,
            )

            all_verts_np = np.array(verts)
            # Get the shape of the vertices for the connection array
            len_verts, dep_verts = np.shape(verts)

            # Make faces connection array taking the vertices in groups of three
            faces_np = np.arange(0, len_verts, 1)
            all_faces_np = faces_np.reshape((-1, dep_verts))
            all_samples_np = np.array(samples)

        else:

            verts_np = np.empty((0, 3))
            faces_np = np.empty((0, 3))
            samples_np = np.empty((0))

            num_grids = len(dregion.index.grids)

            comm.barrier()
            for g in dregion.index.grids[rank:num_grids:size]:

                if do_ghost:
                    g, child_mask = retrieve_ghost_zones(
                        cube=g,
                        n_zones=1,
                        fields=field,
                        ds_left_edge=ds_attributes["left_edge"],
                        ds_right_edge=ds_attributes["right_edge"],
                        single_level=single_level,
                    )
                else:
                    child_mask = g.child_mask
                # Get the physical cell spacing of the grid
                dx, dy, dz = np.array(g.dds)

                if iso_edge:
                    child_mask = (
                        child_mask
                        & (np.array(g[("boxlib", "x")]) >= iso_edge[0])
                        & (np.array(g[("boxlib", "x")]) <= iso_edge[3])
                    )
                    child_mask = (
                        child_mask
                        & (np.array(g[("boxlib", "y")]) >= iso_edge[1])
                        & (np.array(g[("boxlib", "y")]) <= iso_edge[4])
                    )
                    child_mask = (
                        child_mask
                        & (np.array(g[("boxlib", "z")]) >= iso_edge[2])
                        & (np.array(g[("boxlib", "z")]) <= iso_edge[5])
                    )

                # perform smoothing before marching cubes
                if smooth:
                    cube = gaussian_filter(g[field], sigma=smooth)
                else:
                    cube = g[field]

                try:
                    verts, faces, normals, values = marching_cubes(
                        volume=cube,
                        level=value,
                        allow_degenerate=True,
                        step_size=1,
                        gradient_direction="ascent",
                        spacing=(dx, dy, dz),
                        method="lewiner",
                        mask=child_mask,
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

                except RuntimeError:
                    # Skip the regions that are fully masked
                    pass

                # clear the data to reduce memory constraints
                g.clear_data()

            # Explicitly cast the arrays as necessary types
            verts_np = verts_np.astype(np.float64)
            faces_np = faces_np.astype(np.int32)
            samples_np = samples_np.astype(np.float64)

            comm.barrier()
            # gather and combine
            all_verts = comm.gather(verts_np, root=0)
            all_faces = comm.gather(faces_np, root=0)
            all_samples = comm.gather(samples_np, root=0)

            # Barrier before writing
            comm.barrier()
            if rank == 0:
                all_verts_np = np.empty((0, 3), dtype=np.float64)
                all_faces_np = np.empty((0, 3), dtype=np.int32)
                all_samples_np = np.empty((0), dtype=np.float64)

                for i in range(size):
                    # offset the face indices by the current length of the array
                    len_verts, _ = np.shape(all_verts_np)
                    all_faces[i] += len_verts

                    all_verts_np = np.append(all_verts_np, all_verts[i], axis=0)
                    all_faces_np = np.append(all_faces_np, all_faces[i], axis=0)
                    all_samples_np = np.append(all_samples_np, all_samples[i], axis=0)

        # Write out the hdf5 and the xdmf file
        if rank == 0:
            conn_shape, coord_shape, field_shape = write_hdf5(
                verts=all_verts_np,
                samples=all_samples_np,
                faces=all_faces_np,
                field=field,
                fname=os.path.join(outpath, f"{fname}.hdf5"),
            )

            write_xdmf(
                fbase=os.path.join(outpath, fname),
                fhdf5=fname,
                field=field,
                ftype="Scalar",
                ctype="Node" if not do_yt else "Cell",
                value=value,
                time=ds_attributes["time"],
                conn_shape=conn_shape,
                coord_shape=coord_shape,
                field_shape=field_shape,
            )

    else:
        sys.exit(f"Format {outformat} not in [ply, obj, hdf5, xdmf]")


def retrieve_ghost_zones(
    cube,
    n_zones,
    fields,
    ds_left_edge,
    ds_right_edge,
    single_level,
):

    # Get the cube index information
    start_idx = cube.get_global_startindex()
    act_dims = cube.ActiveDimensions

    child_mask = cube.child_mask

    # Define the left and right physical edges we are trying to access
    left_phys = ds_left_edge + (start_idx - n_zones) * cube.dds
    right_phys = left_phys + (act_dims + 2 * n_zones) * cube.dds

    # Get the conditional array to determine which boundary we might cross
    left_cond = left_phys <= ds_left_edge
    right_cond = right_phys >= ds_right_edge

    # Define the new left edge and new dimensions of the box we want
    nl = start_idx - n_zones * np.invert(left_cond)
    new_left_edge = nl * cube.dds + ds_left_edge
    new_dims = (
        act_dims + n_zones * np.invert(left_cond) + n_zones * np.invert(right_cond)
    )

    # Append values to the child mask
    add_left_side = start_idx - nl
    add_right_side = (new_dims - act_dims) - add_left_side

    child_mask = np.append(
        np.full(
            (add_left_side[0], np.shape(child_mask)[1], np.shape(child_mask)[2]),
            False,
            dtype=bool,
        ),
        child_mask,
        axis=0,
    )
    child_mask = np.append(
        np.full(
            (np.shape(child_mask)[0], add_left_side[1], np.shape(child_mask)[2]),
            False,
            dtype=bool,
        ),
        child_mask,
        axis=1,
    )
    child_mask = np.append(
        np.full(
            (np.shape(child_mask)[0], np.shape(child_mask)[1], add_left_side[2]),
            False,
            dtype=bool,
        ),
        child_mask,
        axis=2,
    )

    child_mask = np.append(
        child_mask,
        np.full(
            (add_right_side[0], np.shape(child_mask)[1], np.shape(child_mask)[2]),
            False,
            dtype=bool,
        ),
        axis=0,
    )
    child_mask = np.append(
        child_mask,
        np.full(
            (np.shape(child_mask)[0], add_right_side[1], np.shape(child_mask)[2]),
            False,
            dtype=bool,
        ),
        axis=1,
    )
    child_mask = np.append(
        child_mask,
        np.full(
            (np.shape(child_mask)[0], np.shape(child_mask)[1], add_right_side[2]),
            False,
            dtype=bool,
        ),
        axis=2,
    )

    # Get the new cube that defined by the new covering grid
    cube = cube.ds.covering_grid(
        level=cube.Level if single_level else cube.index.max_level,
        left_edge=new_left_edge,
        dims=new_dims,
    )

    return cube, child_mask


def main():
    """Main function for extracting isosurfaces."""
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    # Parse the input arguments
    args = get_args()

    # Create the output directory
    if rank == 0:
        if args.outpath:
            outpath = args.outpath
        else:
            outpath = os.path.abspath(
                os.path.join(sys.argv[0], "../../outdata", "isosurfaces")
            )
        os.makedirs(outpath, exist_ok=True)

    # Load the plt files
    ts, _ = utils.load_dataseries(
        datapath=args.datapath,
        pname=args.pname,
    )

    comm.Barrier()
    if rank == 0:
        start_time = time.time()

    # Loop over the plt files in the data directory
    for ds in ts:
        # Barrier at the start of each ds iteration
        comm.Barrier()

        # Force periodicity for the yt surface extraction routines...
        if args.format in ["ply", "obj"] or args.yt:
            ds.force_periodicity()

        # Get the updated attributes for the current plt file
        ds_attributes = utils.get_attributes(ds=ds)

        # Create box region the encompasses the domain
        dregion = ds.all_data()

        # Export the isosurfaces in specified format
        if args.value:
            fname = f"isosurface_{args.field}_{args.value}_{ds.basename}"
            value = args.value
        elif args.vfunction:
            vstime = args.vfunction[0]
            vetime = args.vfunction[2]
            vsval = args.vfunction[1]
            veval = args.vfunction[3]
            ds_time = float(ds_attributes["time"])
            if ds_time >= vetime:
                value = veval
            elif ds_time <= vstime:
                value = vsval
            else:
                value = vsval + (veval - vsval) * (
                    (ds_time - vstime) / (vetime - vstime)
                )
            fname = f"isosurface_{args.field}_{ds.basename}_vfunction_{value:.2e}"
            if rank == 0:
                print(f"""The value at time = {ds_time} is {value}.""")
        else:
            sys.exit("must have either value or vfunction defined!")

        if args.yt:
            fname += "_yt"

        do_isosurface_extraction(
            dregion=dregion,
            ds_attributes=ds_attributes,
            outformat=args.format,
            field=args.field,
            value=value,
            outpath=outpath if rank == 0 else None,
            fname=fname,
            comm=comm,
            rank=rank,
            size=size,
            do_ghost=args.do_ghost,
            do_yt=args.yt,
            single_level=args.single_level,
            smooth=args.smooth,
            ds=ds if args.format == "ply" else None,
            iso_edge=args.iso_edge,
        )
        if rank == 0:
            print(
                f"Time to do isosurface extract = {time.time() - start_time} seconds."
            )

    if rank == 0:
        print(f"Elapsed time = {time.time() - start_time} seconds.")


if __name__ == "__main__":
    main()
