import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import yt

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.utilities as utils  # noqa: E402
import ytscripts.ytargs as ytargs  # noqa: E402


def get_args():
    ytparse = ytargs.ytArgs()
    return ytparse.parse_args()


def main():

    args = get_args()

    ts, _ = utils.load_dataseries(
        datapath=args.datapath,
        pname=args.pname,
    )

    base_attributes = utils.get_attributes(ds=ts[0])

    if args.verbose:
        print(f"""The fields in this dataset are: {base_attributes["field_list"]}""")

    for ds in ts:

        # ds.add_field(name=("boxlib","dwdz_manual"), function=_dwdz_manual, sampling_type="cell")

        ds_attributes = utils.get_attributes(ds=ds)
        ds_left_edge = ds_attributes["left_edge"]
        ds_right_edge = ds_attributes["right_edge"]

        ds.force_periodicity()
        dregion = ds.all_data()

        fig, ax = plt.subplots(1, 1)
        fig2, ax2 = plt.subplots(1, 1)

        index = 0
        for g in dregion.index.grids:
            start_idx = g.get_global_startindex()
            act_dims = g.ActiveDimensions
            dx, dy, dz = g.dds

            lx, ly, lz = ds_left_edge
            rx, ry, rz = ds_right_edge

            n_ghost = 1

            nl = start_idx - n_ghost
            new_left_edge = nl * g.dds + ds_left_edge
            new_dims = act_dims + 2 * n_ghost

            elx, ely, elz = np.array(start_idx * g.dds + ds_left_edge)
            erx, ery, erz = (elx, ely, elz) + np.array(act_dims * g.dds)

            extent = [ely, ery, elz, erz]
            print(extent)
            print(index, g.Level, g.index.max_level, g.child_mask.any())

            cube = g.ds.covering_grid(
                # cube = g.ds.smoothed_covering_grid(
                level=g.Level,
                # level=g.index.max_level,
                left_edge=new_left_edge,
                dims=new_dims,
                # num_ghost_zones=2,
            )

            smooth_cube = g.ds.smoothed_covering_grid(
                level=g.Level,
                left_edge=new_left_edge,
                dims=new_dims,
            )

            # dwdz = cube[("boxlib", "dwdz")]
            w = cube[("gas", "velocity_z")]
            smooth_w = smooth_cube[("gas", "velocity_z")]
            # print(dwdz[1, 1, 1])

            # new_cube = np.zeros(act_dims)
            # imax, jmax, kmax = np.array(act_dims)
            imax, jmax, kmax = np.array(new_dims)
            dz = 2.0 * cube[("boxlib", "dz")]

            f = np.zeros_like(
                dz[n_ghost:-n_ghost, n_ghost:-n_ghost, n_ghost:-n_ghost],
                dtype=np.float64,
            )
            f_smooth = np.zeros_like(
                dz[n_ghost:-n_ghost, n_ghost:-n_ghost, n_ghost:-n_ghost],
                dtype=np.float64,
            )
            new_cube = np.zeros_like(dz, dtype=np.float64)
            smooth_cube = np.zeros_like(dz, dtype=np.float64)
            for k in range(kmax):
                for j in range(jmax):
                    for i in range(imax):
                        # f[i, j, k] = (w[i+1, j+1, k+2] - w[i+1, j+1, k])/dz[i+1, j+1, k+1]
                        # f_smooth[i, j, k] = (smooth_w[i+1, j+1, k+2] - smooth_w[i+1, j+1, k])/dz[i+1, j+1, k+1]
                        new_cube[i, j, k] = w[i, j, k]
                        smooth_cube[i, j, k] = smooth_w[i, j, k]

            # new_cube[1:-1, 1:-1, 1:-1] = f
            # smooth_cube[1:-1, 1:-1, 1:-1] = f_smooth

            ax.imshow(
                new_cube[4, :, :].T - smooth_cube[4, :, :].T,
                # new_cube[4,:,:].T,
                # smooth_cube[4,:,:].T,
                origin="lower",
                extent=extent,
                aspect="equal",
                cmap="viridis",
            )

            index += 1

            fig.savefig(os.path.join(args.outpath, f"new_cube_{index}.png"))


if __name__ == "__main__":
    main()
