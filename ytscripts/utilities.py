"""Utility routines used throughout ytscripts."""
import fnmatch
import os

import yt


def load_dataseries(datapath, pname=None, units_override=None):
    """Loads the plt files based on method."""
    if pname is not None:
        load_list = [os.path.join(datapath, x) for x in pname]
        ts = yt.DatasetSeries(load_list, units_override=units_override)
        # Find the index based on location of the selected plot files
        all_files = fnmatch.filter(sorted(os.listdir(datapath)), "plt?????")

        index_list = []
        for plt in pname:
            index_list.append(all_files.index(plt))

    else:
        ts = yt.load(
            os.path.join(datapath, "plt?????"),
            units_override=units_override,
        )

    return ts, index_list
