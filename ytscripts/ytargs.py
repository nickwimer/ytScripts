"""Argument Parser classes for common arguments."""

import argparse
import sys
import tomllib

from ytscripts.utilities import is_notebook


class ytArgs:
    """Base class with standard inputs for yt scripts."""

    def __init__(self):
        """Initialize ytArgs."""
        self.parser = argparse.ArgumentParser()

        # Values that must be set on the command line or in the input file. argparse's
        # own "required" only looks at the command line, so these are checked after
        # the input file has been merged in.
        self.required_args = []
        self.required_groups = []

        # Command line given to parse_args, kept so it can be parsed again on top of
        # the input file
        self._cli_args = None

        self.io_args()

    def get_parser(self):
        """Return the parser."""
        return self.parser

    def parse_args(self, args=None):
        """Return the parsed args."""
        self._cli_args = args
        return self.parser.parse_args(args)

    def get_args(self, args=None):
        """Parse the command line, merge in the input file and return a dict."""
        init_args = self.parse_args(args)
        return self.override_args(init_args, init_args.ifile)

    def add_args_from_dict(self, args):
        """Add arguments from a dictionary."""
        for arg, properties in args.items():
            properties = dict(properties)
            if properties.pop("required", False):
                self.required_args.append(arg)
                properties["help"] = f"""{properties.get("help", "")} (required)"""
            self.parser.add_argument(f"--{arg}", **properties)

    def add_mutually_exclusive_args_from_dict(self, args):
        """Add mutually exclusive arguments from a dictionary (one is needed)."""
        group = self.parser.add_mutually_exclusive_group()
        for arg, properties in args.items():
            group.add_argument(f"--{arg}", **properties)
        self.required_groups.append(list(args))

    def override_args(self, init_args, input_file):
        """Merge the input file with the command line.

        The command line takes precedence over the input file, which takes precedence
        over the parser defaults.
        """
        if input_file:
            with open(input_file, "rb") as f:
                input_options = tomllib.load(f)

            # "title" only describes the input file
            input_options.pop("title", None)

            actions = {action.dest: action for action in self.parser._actions}
            unknown = sorted(set(input_options) - set(actions))
            if unknown:
                print(f"""Ignoring unknown options in {input_file}: {unknown}""")

            defaults = {}
            for key, value in input_options.items():
                if key not in actions:
                    continue
                # Options that take several values always hold a list
                if actions[key].nargs in ("+", "*") and not isinstance(value, list):
                    value = [value]
                defaults[key] = value

            # Use the input file as the defaults and parse the command line again so
            # anything given there still wins
            self.parser.set_defaults(**defaults)
            args = vars(self.parser.parse_args(self._get_cli_args()))
        else:
            args = vars(init_args)

        self.check_required(args)

        return args

    def _get_cli_args(self):
        """Return the command line that was last parsed."""
        if self._cli_args is not None:
            return self._cli_args

        # If the code is being run in a notebook, ignore the kernel's --f argument
        if is_notebook():
            return [arg for arg in sys.argv[1:] if not arg.startswith("--f=")]

        return sys.argv[1:]

    def check_required(self, args):
        """Exit with a usage error if a required value is missing."""
        missing = [f"--{arg}" for arg in self.required_args if args.get(arg) is None]
        missing += [
            " or ".join(f"--{arg}" for arg in group)
            for group in self.required_groups
            if all(args.get(arg) is None for arg in group)
        ]
        if missing:
            self.parser.error(
                "these values must be set on the command line or in the input file: "
                + ", ".join(missing)
            )

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

        if arg in self.required_args:
            self.required_args.remove(arg)

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
                "help": (
                    "Name of contour field, value, and color to plot on top of slice."
                ),
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
                "default": None,
                "help": "Index of the first slice to extract in the normal direction.",
            },
            "max": {
                "type": float,
                "required": True,
                "default": None,
                "help": "Index of the last slice to extract in the normal direction.",
            },
            "num_slices": {
                "type": int,
                "required": True,
                "default": None,
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
                "default": "grid_info",
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
                "required": False,
                "default": ["average_data"],
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
                "required": False,
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
