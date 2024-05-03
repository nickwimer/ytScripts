"""Argument Parser classes for common arguments."""

import argparse
import sys
import tomllib

from pydantic.v1.utils import deep_update

from ytscripts.utilities import is_notebook


class ytArgs:
    """Base class with standard inputs for yt scripts."""

    def __init__(self):
        """Initialize ytArgs."""
        self.parser = argparse.ArgumentParser()

        self.io_args()

    def parse_args(self, args=None):
        """Return the parsed args."""
        return (
            self.parser.parse_args() if args is None else self.parser.parse_args(args)
        )

    def add_args_from_dict(self, args):
        """Add arguments from a dictionary."""
        for arg, properties in args.items():
            self.parser.add_argument(f"--{arg}", **properties)

    def add_mutually_exclusive_args_from_dict(self, args):
        """Add mutually exclusive arguments from a dictionary."""
        group = self.parser.add_mutually_exclusive_group(required=True)
        for arg, properties in args.items():
            group.add_argument(f"--{arg}", **properties)

    def override_args(self, init_args, input_file):
        """Override CLI arguments with those from input file."""
        if input_file:
            with open(input_file, "rb") as f:
                input_options = tomllib.load(f)

            # Now combine the two with preference to the input file
            args = deep_update(vars(init_args), input_options)

            # If the code is being run in a notebook, ignore --f argument
            if is_notebook():
                sys_args = [arg for arg in sys.argv if not arg.startswith("--f=")]
            else:
                sys_args = sys.argv

            # Update any manually specified arguments
            for indx, iarg in enumerate(sys_args):
                if "-" in iarg[0]:
                    user_arg = iarg.replace("-", "")

                    # Check to see if arg is a flag
                    if type(args[user_arg]) is bool:
                        args = deep_update(args, {user_arg: True})
                    else:
                        args = deep_update(args, {user_arg: sys_args[indx + 1]})
        else:
            args = vars(init_args)

        return args

    # TODO: remove argument from dictionary instead of dealing with it in the parser
    #      need to return the updated dictionary for all functions, then update the
    #      parser at the end (or in the main script)
    # def remove_arg_from_dict(self, args, rm_arg):
    #     """Remove argument from dictionary."""
    #     if rm_arg in args:
    #         del args[rm_arg]
    #     return args

    def remove_arg(self, arg):
        """Remove argument from parser."""
        for action in self.parser._actions:
            opts = action.option_strings
            if (opts and opts[0] == arg) or action.dest == arg:
                self.parser._remove_action(action)
                break

        for action in self.parser._action_groups:
            for group_action in action._group_actions:
                if group_action.dest == arg:
                    action._group_actions.remove(group_action)
                    return

    def io_args(self):
        """Add I/O arguments."""

        args = {
            "datapath": {
                "type": str,
                "required": False,
                "default": None,
                "help": "Path to the data files.",
            },
            "outpath": {
                "type": str,
                "required": False,
                "default": None,
                "help": "Path to the output directory.",
            },
            "pname": {
                "type": str,
                "nargs": "+",
                "required": False,
                "default": None,
                "help": "Name of plt files to plot (if empty, do all)",
            },
            "field": {
                "type": str,
                "required": False,
                "default": None,
                "help": "Name of the field for visualization.",
            },
            "SI": {
                "action": "store_true",
                "help": "Flag to set the units to SI (default is cgs).",
            },
            "verbose": {
                "action": "store_true",
                "help": "Flag to turn on various statements.",
            },
            "no_mpi": {
                "action": "store_true",
                "help": "Flag to manually disable mpi features.",
            },
            "nprocs": {
                "type": int,
                "required": False,
                "default": 1,
                "help": (
                    "Number of processors to devote to each file when operating in"
                    "parallel mode"
                ),
            },
            "nskip": {
                "type": int,
                "required": False,
                "default": None,
                "help": """Skip every "nskip" entries in "pname" list.""",
            },
            "ifile": {
                "type": str,
                "required": False,
                "default": None,
                "help": "Path to the input file for configuring plots.",
            },
        }

        # Add arguments from dict to parser
        self.add_args_from_dict(args)

    def orientation_args(self):
        """Add 2D slicing arguments."""

        args = {
            "normal": {
                "type": str,
                "required": False,
                "default": "z",
                "help": "Normal direction for the slice plot.",
            },
            "grid_offset": {
                "type": float,
                "required": False,
                "default": 0.0,
                "help": "Amount to offset center to avoid grid alignment vis issues.",
            },
        }

        # Add arguments from dict to parser
        self.add_args_from_dict(args)

    def vis_2d_args(self):
        """Add 2D visualization arguments."""

        args = {
            "cmap": {
                "type": str,
                "required": False,
                "default": "dusk",
                "help": "Colormap for the 2D plot.",
            },
            "dpi": {
                "type": int,
                "required": False,
                "default": 300,
                "help": "dpi of the output image (default = 300).",
            },
            "pbox": {
                "type": float,
                "nargs": "+",
                "required": False,
                "default": None,
                "help": (
                    "Bounding box of the plot specified by the two corners "
                    "(x0 y0 x1 y1)."
                ),
            },
            "fbounds": {
                "type": float,
                "nargs": "+",
                "required": False,
                "default": None,
                "help": "Bounds for the colorbar.",
            },
        }

        # Add arguments from dict to parser
        self.add_args_from_dict(args)


class ytVisArgs(ytArgs):
    """Class to interface with standard yt visualization functions."""

    def __init__(self, **kwargs):
        """Initialize ytVisArgs."""
        super(ytVisArgs, self).__init__(**kwargs)

    def slice_args(self):
        """Add arguments for SlicePlot."""

        args = {
            "center": {
                "type": float,
                "nargs": "+",
                "required": False,
                "default": None,
                "help": "Coordinate list for center of slice plot (x, y, z).",
            },
            "plot_log": {
                "action": "store_true",
                "help": "Plot in log values.",
            },
            "grids": {
                "type": float,
                "nargs": "+",
                "required": False,
                "default": None,
                "help": (
                    "Options to specify annotate grids (alpha, min_level, max_level, "
                    "linewidth)."
                ),
            },
            "cells": {
                "type": str,
                "nargs": "+",
                "required": False,
                "default": None,
                "help": "Options to specify annotate cells (linewidth, alpha, color).",
            },
            "buff": {
                "type": int,
                "nargs": "+",
                "required": False,
                "default": None,
                "help": "Buffer for the SlicePlot image for plotting.",
            },
            "contour": {
                "type": str,
                "nargs": "+",
                "required": False,
                "default": None,
                "help": "Name of contour field and value to plot on top of slice.",
            },
            "clw": {
                "type": float,
                "nargs": "+",
                "required": False,
                "default": None,
                "help": "Linewidth for each of the contour lines.",
            },
            "pickle": {
                "action": "store_true",
                "help": "Flag to store image as pickle for later manipulation.",
            },
            "grid_info": {
                "type": float,
                "nargs": "+",
                "required": False,
                "default": None,
                "help": (
                    "Add text box with grid information (xloc, yloc, min_lev, max_lev)."
                ),
            },
            "rm_eb": {
                "type": float,
                "required": False,
                "default": None,
                "help": "Float value to plot non-fluid using binary cmap [0, 1].",
            },
            "gradient": {
                "type": str,
                "choices": ["x", "y", "z", "magnitude"],
                "required": False,
                "default": None,
                "help": "Choice to visualize the gradient of the input field.",
            },
            "no_time": {
                "action": "store_true",
                "help": "Flag to remove the timestamp.",
            },
            "no_units": {
                "action": "store_true",
                "help": "Flag to remove all units from plots.",
            },
            "add_udf": {
                "type": str,
                "required": False,
                "default": None,
                "help": "Name of user defined functions file (located in udfs/).",
            },
            "use_tex": {
                "action": "store_true",
                "help": "Flag to use latex parser.",
            },
        }

        # Add arguments from dict to parser
        self.add_args_from_dict(args)


class ytExtractArgs(ytArgs):
    """Class to interface with custom data extraction functions."""

    def __init__(self, **kwargs):
        """Initialize ytExtractArgs."""
        super(ytExtractArgs, self).__init__(**kwargs)

    def slice_args(self):
        """Add arguments for extract slices routine."""

        args = {
            "min": {
                "type": float,
                "required": True,
                "help": "Index of the first slice to extract in the normal direction.",
            },
            "max": {
                "type": float,
                "required": True,
                "help": "Index of the last slice to extract in the normal direction.",
            },
            "num_slices": {
                "type": int,
                "required": True,
                "help": "Number of slices to extract in normal direction.",
            },
            "gradient": {
                "type": str,
                "choices": ["x", "y", "z", "magnitude"],
                "required": False,
                "default": None,
                "help": "Choice to extract the gradient of the input field.",
            },
        }

        # Add arguments from dict to parser
        self.add_args_from_dict(args)

    def isosurface_args(self):
        """Add arguments for extracting iso-surfaces."""

        val_args = {
            "value": {
                "type": float,
                "help": "Value of the iso surface to extract.",
            },
            "vfunction": {
                "type": float,
                "nargs": "+",
                "help": (
                    "Value of the iso surface to extract as a function "
                    "(start_time; start_value; end_time; end_value)."
                ),
            },
        }

        args = {
            "format": {
                "type": str,
                "required": False,
                "default": "ply",
                "help": "Output format of the iso-surface.",
            },
            "yt": {
                "action": "store_true",
                "help": (
                    "Flag to enable yt iso-surface extraction when outputting in "
                    "hdf5/xdmf format only (default to faster, custom routine)."
                ),
            },
            "do_ghost": {
                "action": "store_true",
                "help": "Flag to get ghost cells before the iso-surface extraction.",
            },
            "single_level": {
                "action": "store_true",
                "help": "Flag to only get single grid level for isosurface.",
            },
            "smooth": {
                "type": float,
                "required": False,
                "default": None,
                "help": "Smoothing value to apply to field before isosurface extract",
            },
            "iso_edge": {
                "type": float,
                "nargs": "+",
                "required": False,
                "default": None,
                "help": "Physical box inside which we extract isosurfaces.",
            },
            "gradient": {
                "type": str,
                "choices": ["x", "y", "z", "magnitude"],
                "required": False,
                "default": None,
                "help": "Choice to extract the gradient of the input field.",
            },
        }

        # Add arguments from dict to parser
        self.add_args_from_dict(args)
        # Add mutually exclusive arguments from dict to parser
        self.add_mutually_exclusive_args_from_dict(val_args)

    def average_args(self):
        """Add arguments for extracting averages."""

        args = {
            "fields": {
                "type": str,
                "nargs": "+",
                "required": True,
                "default": None,
                "help": "Names of the data fields to extract.",
            },
            "name": {
                "type": str,
                "required": False,
                "default": "average_data",
                "help": "Name of the output data file (.pkl).",
            },
            "normal": {
                "type": str,
                "choices": ["x", "y", "z"],
                "required": False,
                "default": None,
                "help": "Option to perform 2D slice (defaults to domain average).",
            },
            "location": {
                "type": float,
                "required": False,
                "default": None,
                "help": (
                    "Physical location to perform the 2D slice (if normal is defined)."
                ),
            },
            "rm_eb": {
                "action": "store_true",
                "help": "Flag to explicitly remove all data in EB regions.",
            },
        }

        # Add arguments from dict to parser
        self.add_args_from_dict(args)

        # remove potentially conflicting arguments from base class
        self.remove_arg("field")

    def grid_args(self):
        """Add arguments for extracting grid info."""

        args = {
            "name": {
                "type": str,
                "required": False,
                "default": "average_data",
                "help": "Name of the output data file (.pkl).",
            },
        }

        # Add arguments from dict to parser
        self.add_args_from_dict(args)

        # remove potentially conflicting arguments from base class
        self.remove_arg("field")


class ytPlotArgs(ytArgs):
    """Class to interface with custom plot functions."""

    def __init__(self, **kwargs):
        """Initialize ytPlotArgs."""
        super(ytPlotArgs, self).__init__(**kwargs)

        # remove unused arguments from base class
        self.remove_arg("pname")
        self.remove_arg("SI")

    def slice_args(self):
        """Add arguments for plotting slices."""
        self.vis_2d_args()

    def average_args(self):
        """Add arguments for plotting averages."""

        args = {
            "fields": {
                "type": str,
                "nargs": "+",
                "required": True,
                "default": None,
                "help": "Names of the data fields to plot.",
            },
            "fname": {
                "type": str,
                "nargs": "+",
                "required": True,
                "default": "average_data",
                "help": "Name of the data file to load and plot (.pkl).",
            },
            "dpi": {
                "type": int,
                "required": False,
                "default": 300,
                "help": "dpi of the output image (default = 300).",
            },
        }

        # Add arguments from dict to parser
        self.add_args_from_dict(args)

        # remove potentially conflicting arguments from base class
        self.remove_arg("field")

    def grid_args(self):
        """Add arguments for plotting grid info."""

        args = {
            "fname": {
                "type": str,
                "required": True,
                "default": "grid_info",
                "help": "Name of the data file to load and plot (.pkl).",
            },
            "dpi": {
                "type": int,
                "required": False,
                "default": 300,
                "help": "dpi of the output image (default = 300).",
            },
            "ptype": {
                "type": str,
                "required": False,
                "choices": ["line", "pie", "bar"],
                "default": "line",
                "help": "type of plot to make.",
            },
        }

        # Add arguments from dict to parser
        self.add_args_from_dict(args)

        # remove potentially conflicting arguments from base class
        self.remove_arg("field")


class ytAnalysisArgs(ytArgs):
    """Class to interface with custom data analysis functions."""

    def __init__(self, **kwargs):
        """Initialize ytAnalysisArgs."""
        super(ytAnalysisArgs, self).__init__(**kwargs)

    def mixture_fraction(self):
        """Add in arguments for analyzing mixture fraction data."""

        args = {
            "name": {
                "type": str,
                "required": False,
                "default": "mixture_average",
                "help": "Name of the output data file (.pkl).",
            },
            "rm_eb": {
                "required": False,
                "action": "store_true",
                "help": "Flag to explicitly remove all data in EB regions.",
            },
            "nbins": {
                "required": False,
                "type": int,
                "default": 10,
                "help": "Number of bins to use for the mixture fraction averaging.",
            },
        }

        # Add arguments from dict to parser
        self.add_args_from_dict(args)

        # remove potentially conflicting arguments from base class
        self.remove_arg("field")
