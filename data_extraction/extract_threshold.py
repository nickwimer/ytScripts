"""Extracts the cells above a threshold value from plot files and saves."""

import os
import sys
import time

import h5py
import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402

# Columns that describe each cell, before the field and any extra fields
CELL_COLUMNS = ["x", "y", "z", "dx", "dy", "dz", "level"]


def get_parser():
    """Get the parser."""
    ytparse = ytargs.ytExtractArgs()
    # Add in the arguments for the extract threshold
    ytparse.threshold_args()

    return ytparse


def get_base_parser():
    """Get the base level parser primarily for documentation."""
    return get_parser().get_parser()


def get_args(parser, cli_args=None):
    """Get the arguments from the parser (cli_args defaults to sys.argv)."""
    # Parse the command line, merged with the input file if one is given
    args = parser.get_args(cli_args)

    if args["vfunction"] is not None and len(args["vfunction"]) != 4:
        parser.get_parser().error(
            "--vfunction needs four values: start_time start_value end_time end_value"
        )

    if (
        args["max"] is not None
        and args["value"] is not None
        and args["max"] <= args["value"]
    ):
        parser.get_parser().error("--max must be larger than --value")

    if args["bounds"] is not None:
        if len(args["bounds"]) != 6:
            parser.get_parser().error(
                "--bounds needs six values: xlo ylo zlo xhi yhi zhi"
            )
        if any(lo >= hi for lo, hi in zip(args["bounds"][:3], args["bounds"][3:])):
            parser.get_parser().error("--bounds needs each low value below its high")

    # Return the parsed arguments as a dict
    return args


def threshold_value(vfunction, ds_time):
    """Return the threshold at a time, from (start_time, start_value, end_time,
    end_value), held constant outside of the start and end times."""
    vstime, vsval, vetime, veval = vfunction
    if ds_time >= vetime:
        return veval
    elif ds_time <= vstime:
        return vsval
    return vsval + (veval - vsval) * ((ds_time - vstime) / (vetime - vstime))


def threshold_mask(values, child_mask, value, vmax=None, coords=None, bounds=None):
    """Return the mask of the finest-level cells within the threshold.

    ``child_mask`` is False where a finer grid covers the cell, so each location is
    only kept once. ``coords`` holds the (x, y, z) cell centers, and is only needed
    with ``bounds`` (xlo, ylo, zlo, xhi, yhi, zhi).
    """
    values = np.asarray(values)
    mask = np.asarray(child_mask, dtype=bool) & (values > value)
    if vmax is not None:
        mask &= values < vmax
    if bounds is not None:
        for pos, lo, hi in zip(coords, bounds[:3], bounds[3:]):
            pos = np.asarray(pos)
            mask &= (pos >= lo) & (pos <= hi)

    return mask


def cells_to_dataframe(cells, field, extra_fields, attrs):
    """Put the kept cells into a table with one row per cell."""
    columns = [*CELL_COLUMNS, field, *extra_fields]
    df = pd.DataFrame({col: cells[col] for col in columns}, columns=columns)

    # Keep what the table holds with the data
    df.attrs.update(attrs)

    return df


def write_hdf5(cells, field, fname, extra_fields=(), attrs=None):
    """Write the HDF5 file based on the kept cells."""
    with h5py.File(fname, "w") as f:
        coords = np.column_stack([cells[col] for col in ("x", "y", "z")])
        dds = np.column_stack([cells[col] for col in ("dx", "dy", "dz")])
        f.create_dataset("Coord", data=coords, dtype=np.float64)
        f.create_dataset("dds", data=dds, dtype=np.float64)
        f.create_dataset("Level", data=cells["level"], dtype=np.int32)
        for name in [field, *extra_fields]:
            f.create_dataset(name, data=cells[name], dtype=np.float64)

        # hdf5 attributes can not hold None or dicts
        for key, value in (attrs or {}).items():
            if value is None:
                continue
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    f.attrs[f"{key}_{subkey}"] = subvalue
            else:
                f.attrs[key] = value

    return np.shape(coords)


def write_xdmf(fbase, fhdf5, field, value, time, coord_shape, extra_fields=()):
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
        f"""\t\t<Grid Name="threshold" GridType="Uniform">\n"""
        f"""\t\t<Information Name="Variable" Value="{field}"/>\n"""
        f"""\t\t<Information Name="Threshold" Value="{value}"/>\n"""
        f"""\t\t<Time Value="{time}"/>\n"""
    )

    # Form the Topology block, with each cell as one point
    xdmf_file.write(
        f"""\t\t\t<Topology TopologyType="Polyvertex" NumberOfElements="""
        f""""{coord_shape[0]}" NodesPerElement="1"/>\n"""
    )

    # Form the Geometry block
    xdmf_file.write(
        f"""\t\t\t<Geometry GeometryType="XYZ">\n"""
        f"""\t\t\t\t<DataItem Name="Coord" Format="HDF" DataType="Float" """
        f"""Precision="8" Dimensions="{coord_shape[0]} {coord_shape[1]}">\n"""
        f"""\t\t\t\t\t{fhdf5}.hdf5:/Coord\n"""
        f"""\t\t\t\t</DataItem>\n"""
        f"""\t\t\t</Geometry>\n"""
    )

    # Form an Attribute block for the cell size, which has three values per point
    xdmf_file.write(
        """\t\t\t<Attribute Name="dds" AttributeType="Vector" Center="Node">\n"""
        f"""\t\t\t\t<DataItem Format="HDF" DataType="Float" Precision="8" """
        f"""Dimensions="{coord_shape[0]} 3">\n"""
        f"""\t\t\t\t\t{fhdf5}.hdf5:/dds\n"""
        f"""\t\t\t\t</DataItem>\n"""
        f"""\t\t\t</Attribute>\n"""
    )

    # Form an Attribute block for the level, the field and any extra fields, which
    # all have one value per point
    attributes = [("Level", "Int", 4)]
    attributes += [(attr, "Float", 8) for attr in [field, *extra_fields]]
    for attr, dtype, precision in attributes:
        xdmf_file.write(
            f"""\t\t\t<Attribute Name="{attr}" AttributeType="Scalar" """
            f"""Center="Node">\n"""
            f"""\t\t\t\t<DataItem Format="HDF" DataType="{dtype}" """
            f"""Precision="{precision}" Dimensions="{coord_shape[0]}">\n"""
            f"""\t\t\t\t\t{fhdf5}.hdf5:/{attr}\n"""
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


def empty_cells(columns):
    """Return a cell dict with no cells in it."""
    cells = {col: np.empty((0), dtype=np.float64) for col in columns}
    cells["level"] = np.empty((0), dtype=np.int32)
    return cells


def concatenate_cells(cell_list, columns):
    """Join a list of cell dicts into one, in the order of the list."""
    if not cell_list:
        return empty_cells(columns)
    return {col: np.concatenate([cells[col] for cells in cell_list]) for col in columns}


def get_units(data, field, extra_fields, length_unit):
    """Return the units of each column, read from a data object."""
    units = {col: length_unit for col in CELL_COLUMNS if col != "level"}
    units["level"] = ""
    for name in [field, *extra_fields]:
        units[name] = str(data[name].units)
    return units


def yt_threshold_cells(
    ds, dregion, field, value, length_unit, vmax=None, bounds=None, extra_fields=()
):
    """Return the kept cells and their units using the yt cut_region."""
    conditions = [f"obj[{field!r}] > {value!r}"]
    if vmax is not None:
        conditions.append(f"obj[{field!r}] < {vmax!r}")
    if bounds is not None:
        for axis, lo, hi in zip("xyz", bounds[:3], bounds[3:]):
            conditions.append(f"obj['index', '{axis}'] >= {lo!r}")
            conditions.append(f"obj['index', '{axis}'] <= {hi!r}")

    cut = ds.cut_region(dregion, conditions)

    cells = {}
    for axis in "xyz":
        cells[axis] = cut["index", axis].to(length_unit).d
        cells[f"d{axis}"] = cut["index", f"d{axis}"].to(length_unit).d
    cells["level"] = cut["index", "grid_level"].d.astype(np.int32)
    for name in [field, *extra_fields]:
        cells[name] = cut[name].d.astype(np.float64)

    return cells, get_units(cut, field, extra_fields, length_unit)


def do_threshold_extraction(
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
    vmax=None,
    bounds=None,
    do_yt=False,
    ds=None,
    extra_fields=None,
):
    """Do the threshold extraction according to the input parameters."""
    # Other fields to store in the cells, skipping repeats and the field itself
    extra_fields = [f for f in dict.fromkeys(extra_fields or []) if f != field]
    columns = [*CELL_COLUMNS, field, *extra_fields]
    length_unit = str(ds_attributes["length_unit"].units)

    if do_yt:
        # Every rank does the same work, and the root writes it
        all_cells, units = yt_threshold_cells(
            ds=ds,
            dregion=dregion,
            field=field,
            value=value,
            length_unit=length_unit,
            vmax=vmax,
            bounds=bounds,
            extra_fields=extra_fields,
        )

    else:
        cell_list = []
        units = {}

        num_grids = len(dregion.index.grids)

        comm.barrier()
        for g in dregion.index.grids[rank:num_grids:size]:
            values = g[field]
            if not units:
                units = get_units(g, field, extra_fields, length_unit)

            # The cell centers are only needed to check the bounds
            coords = None
            if bounds is not None:
                coords = [g["index", axis].to(length_unit).d for axis in "xyz"]

            mask = threshold_mask(
                values=values,
                child_mask=g.child_mask,
                value=value,
                vmax=vmax,
                coords=coords,
                bounds=bounds,
            )

            ncells = int(np.count_nonzero(mask))
            if ncells:
                if coords is None:
                    coords = [g["index", axis].to(length_unit).d for axis in "xyz"]
                dds = g.dds.to(length_unit).d

                cells = {}
                for idx, axis in enumerate("xyz"):
                    cells[axis] = coords[idx][mask]
                    cells[f"d{axis}"] = np.full(ncells, dds[idx])
                cells["level"] = np.full(ncells, g.Level, dtype=np.int32)
                cells[field] = np.asarray(values, dtype=np.float64)[mask]
                for efield in extra_fields:
                    cells[efield] = np.asarray(g[efield], dtype=np.float64)[mask]
                cell_list.append(cells)

            # clear the data to reduce memory constraints
            g.clear_data()

        cells_np = concatenate_cells(cell_list, columns)

        comm.barrier()
        # gather and combine
        all_cells = comm.gather(cells_np, root=0)
        all_units = comm.gather(units, root=0)

        # Barrier before writing
        comm.barrier()
        if rank == 0:
            # Combine the cells in rank order
            all_cells = concatenate_cells(all_cells, columns)
            units = next((u for u in all_units if u), {})

    # Write out the cells
    if rank == 0:
        attrs = {
            "field": field,
            "threshold": value,
            "max": vmax,
            "bounds": list(bounds) if bounds is not None else None,
            "time": float(ds_attributes["time"]),
            "units": units,
        }
        ncells = len(all_cells["level"])

        if outformat == "pkl":
            df = cells_to_dataframe(all_cells, field, extra_fields, attrs)
            df.to_pickle(os.path.join(outpath, f"{fname}.pkl"))
            saved = f"{fname}.pkl"

        elif outformat in ["hdf5", "xdmf"]:
            # xdmf or hdf5 will write the hdf5 file and the xdmf wrapper file
            coord_shape = write_hdf5(
                cells=all_cells,
                field=field,
                fname=os.path.join(outpath, f"{fname}.hdf5"),
                extra_fields=extra_fields,
                attrs=attrs,
            )

            write_xdmf(
                fbase=os.path.join(outpath, fname),
                fhdf5=fname,
                field=field,
                value=value,
                time=attrs["time"],
                coord_shape=coord_shape,
                extra_fields=extra_fields,
            )
            saved = f"{fname}.hdf5 and {fname}.xmf"

        else:
            sys.exit(f"Format {outformat} not in [pkl, hdf5, xdmf]")

        print(f"Saved {ncells} cells to {saved} in {outpath}")

        return ncells


def main():
    """Main function for extracting the cells above a threshold."""
    # Parse the input arguments
    parser = get_parser()
    args = get_args(parser)

    # Share the grids over MPI only when launched with mpirun or srun
    comm = utils.get_mpi_comm(no_mpi=args["no_mpi"])
    if comm is None:
        comm = utils.SerialComm()
    rank = comm.Get_rank()
    size = comm.Get_size()

    # Create the output directory
    outpath = None
    if rank == 0:
        if args["outpath"]:
            outpath = args["outpath"]
        else:
            outpath = os.path.abspath(
                os.path.join(sys.argv[0], "../../outdata", "threshold")
            )
        os.makedirs(outpath, exist_ok=True)

    # Load the plt files
    ts, _ = utils.load_dataseries(
        datapath=args["datapath"],
        pname=args["pname"],
        nskip=args["nskip"],
    )

    base_attributes = utils.get_attributes(ds=ts[0])

    if args["verbose"] and rank == 0:
        print(f"""The fields in this dataset are: {base_attributes["field_list"]}""")

    comm.Barrier()
    if rank == 0:
        start_time = time.time()

    # Loop over the plt files in the data directory
    for ds in ts:
        # Barrier at the start of each ds iteration
        comm.Barrier()
        if rank == 0:
            ds_start_time = time.time()

        # Threshold the gradient field, if requested
        if args["gradient"]:
            vis_field = utils.get_gradient_field(ds, args["field"], args["gradient"])
        else:
            vis_field = args["field"]

        # Get the updated attributes for the current plt file
        ds_attributes = utils.get_attributes(ds=ds)

        # Create box region the encompasses the domain
        dregion = ds.all_data()

        # Get the threshold for this plt file
        if args["value"] is not None:
            value = args["value"]
            fname = f"""threshold_{vis_field}_{value}_{ds.basename}"""
        elif args["vfunction"] is not None:
            ds_time = float(ds_attributes["time"])
            value = threshold_value(args["vfunction"], ds_time)
            fname = f"threshold_{vis_field}_{ds.basename}_vfunction_{value:.2e}"
            if rank == 0:
                print(f"""The value at time = {ds_time} is {value}.""")
        else:
            sys.exit("must have either value or vfunction defined!")

        if args["max"] is not None:
            if args["max"] <= value:
                sys.exit(f"""--max {args["max"]} must be larger than {value}""")
            fname += f"""_max{args["max"]}"""

        if args["yt"]:
            fname += "_yt"

        do_threshold_extraction(
            dregion=dregion,
            ds_attributes=ds_attributes,
            outformat=args["format"],
            field=vis_field,
            value=value,
            outpath=outpath,
            fname=fname,
            comm=comm,
            rank=rank,
            size=size,
            vmax=args["max"],
            bounds=args["bounds"],
            do_yt=args["yt"],
            ds=ds,
            extra_fields=args["extra_fields"],
        )
        if rank == 0:
            print(
                f"Time to do threshold extract = {time.time() - ds_start_time} "
                "seconds."
            )

    if rank == 0:
        print(f"Elapsed time = {time.time() - start_time} seconds.")


if __name__ == "__main__":
    main()
