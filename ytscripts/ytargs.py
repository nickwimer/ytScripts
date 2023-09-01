"""Argument Parser classes for common arguments."""
import argparse


class ytArgs:
    """Base class with standard inputs for yt scripts."""

    def __init__(self):
        """Initialize ytArgs."""
        self.parser = argparse.ArgumentParser()

        self.io_args()

    def parse_args(self):
        """Return the parsed args."""
        return self.parser.parse_args()

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
        self.parser.add_argument(
            "-p",
            "--datapath",
            type=str,
            required=True,
            help="Path to the data files.",
        )
        self.parser.add_argument(
            "-o",
            "--outpath",
            type=str,
            required=False,
            default=None,
            help="Path to the output directory.",
        )
        self.parser.add_argument(
            "--pname",
            type=str,
            nargs="+",
            required=False,
            default=None,
            help="Name of plt files to plot (if empty, do all)",
        )
        self.parser.add_argument(
            "--field",
            type=str,
            required=True,
            help="Name of the field for visualization.",
        )
        self.parser.add_argument(
            "--SI",
            action="store_true",
            help="Flag to set the units to SI (default is cgs).",
        )
        self.parser.add_argument(
            "--verbose",
            action="store_true",
            help="Flag to turn on various statements.",
        )
        self.parser.add_argument(
            "--no_mpi",
            action="store_true",
            help="Flag to manually disable mpi features.",
        )
        self.parser.add_argument(
            "--nprocs",
            type=int,
            required=False,
            default=1,
            help=(
                "Number of processors to devote to each file when operating in"
                "parallel mode"
            ),
        )
        self.parser.add_argument(
            "--nskip",
            type=int,
            required=False,
            default=None,
            help="""Skip every "nskip" entries in "pname" list""",
        )

    def orientation_args(self):
        """Add 2D slicing arguments."""
        self.parser.add_argument(
            "--normal",
            type=str,
            required=True,
            help="Normal direction for the slice plot.",
        )
        self.parser.add_argument(
            "--grid_offset",
            type=float,
            required=False,
            default=0.0,
            help="Amount to offset center to avoid grid alignment vis issues.",
        )

    def vis_2d_args(self):
        self.parser.add_argument(
            "--cmap",
            type=str,
            required=False,
            default="dusk",
            help="Colormap for the 2D plot.",
        )
        self.parser.add_argument(
            "--dpi",
            type=int,
            required=False,
            default=300,
            help="dpi of the output image (default = 300).",
        )
        self.parser.add_argument(
            "--pbox",
            type=float,
            nargs="+",
            required=False,
            default=None,
            help="Bounding box of the plot specified by the two corners (x0 y0 x1 y1).",
        )
        self.parser.add_argument(
            "--fbounds",
            type=float,
            nargs="+",
            required=False,
            default=None,
            help="Bounds for the colorbar.",
        )


class ytVisArgs(ytArgs):
    """Class to interface with standard yt visualization functions."""

    def __init__(self, **kwargs):
        """Initialize ytVisArgs."""
        super(ytVisArgs, self).__init__(**kwargs)

    def slice_args(self):
        """Add arguments for SlicePlot."""
        self.parser.add_argument(
            "-c",
            "--center",
            nargs="+",
            type=float,
            required=False,
            help="Coordinate list for center of slice plot (x, y, z).",
        )
        self.parser.add_argument(
            "--plot_log",
            action="store_true",
            help="Plot in log values.",
        )
        self.parser.add_argument(
            "--grids",
            type=float,
            nargs="+",
            # action="store_true",
            default=None,
            help=(
                "Options to specify annotate grids (alpha, min_level, max_level, "
                "linewidth)."
            ),
        )
        self.parser.add_argument(
            "--cells",
            type=str,
            nargs="+",
            # action="store_true",
            default=False,
            help=("Options to specify annotate cells (linewidth, alpha, color)",),
        )
        self.parser.add_argument(
            "--buff",
            type=int,
            nargs="+",
            required=False,
            default=None,
            help="Buffer for the SlicePlot image for plotting.",
        )
        self.parser.add_argument(
            "--contour",
            type=str,
            nargs="+",
            required=False,
            default=None,
            help="Name of contour field and value to plot on top of slice.",
        )
        self.parser.add_argument(
            "--clw",
            type=float,
            nargs="+",
            required=False,
            default=None,
            help="Linewidth for each of the contour lines.",
        )
        self.parser.add_argument(
            "--pickle",
            action="store_true",
            help="Flag to store image as pickle for later manipulation.",
        )
        self.parser.add_argument(
            "--grid_info",
            type=float,
            nargs="+",
            default=None,
            help="Add text box with grid information (xloc, yloc, min_lev, max_lev).",
        )
        self.parser.add_argument(
            "--rm_eb",
            type=float,
            required=False,
            default=None,
            help="Float value to plot non-fluid using binary cmap [0, 1].",
        )
        self.parser.add_argument(
            "--gradient",
            type=str,
            choices=["x", "y", "z", "magnitude"],
            required=False,
            default=None,
            help="Choice to visualize the gradient of the input field.",
        )
        self.parser.add_argument(
            "--no_time",
            action="store_true",
            help="Flag to remove the timestamp.",
        )
        self.parser.add_argument(
            "--no_units",
            action="store_true",
            help="Flag to remove all units from plots.",
        )


class ytExtractArgs(ytArgs):
    """Class to interface with custom data extraction functions."""

    def __init__(self, **kwargs):
        """Initialize ytExtractArgs."""
        super(ytExtractArgs, self).__init__(**kwargs)

    def slice_args(self):
        """Add arguments for extract slices routine."""
        self.parser.add_argument(
            "--min",
            type=float,
            required=True,
            help="Index of the first slice to extract in the normal direction.",
        )
        self.parser.add_argument(
            "--max",
            type=float,
            required=True,
            help="Index of the last slice to extract in the normal direction.",
        )
        self.parser.add_argument(
            "--num_slices",
            type=int,
            required=True,
            help="Number of slices to extract in normal direction.",
        )
        self.parser.add_argument(
            "--gradient",
            type=str,
            choices=["x", "y", "z", "magnitude"],
            required=False,
            default=None,
            help="Choice to extract the gradient of the input field.",
        )

    def isosurface_args(self):
        """Add arguments for extracting iso-surfaces."""
        val_group = self.parser.add_mutually_exclusive_group(required=True)
        val_group.add_argument(
            "--value",
            type=float,
            help="Value of the iso surface to extract.",
        )
        val_group.add_argument(
            "--vfunction",
            type=float,
            nargs="+",
            help=(
                "Value of the iso surface to extract as a function "
                "(start_time; start_value; end_time1; end_value)."
            ),
        )

        self.parser.add_argument(
            "--format",
            type=str,
            required=False,
            default="ply",
            help="Output format of the iso-surface.",
        )
        self.parser.add_argument(
            "--yt",
            action="store_true",
            help=(
                "Flag to enable yt iso-surface extraction when outputting in "
                "hdf5/xdmf format only (default to faster, custom routine)."
            ),
        )
        self.parser.add_argument(
            "--do_ghost",
            action="store_true",
            help="Flag to get ghost cells before the iso-surface extraction.",
        )
        self.parser.add_argument(
            "--single_level",
            action="store_true",
            help="Flag to only get single grid level for isosurface.",
        )
        self.parser.add_argument(
            "--smooth",
            type=float,
            required=False,
            default=None,
            help="Smoothing value to apply to field before isosurface extract",
        )
        self.parser.add_argument(
            "--iso_edge",
            type=float,
            nargs="+",
            required=False,
            default=None,
            help="Physical box inside which we extract isosurfaces.",
        )
        self.parser.add_argument(
            "--gradient",
            type=str,
            choices=["x", "y", "z", "magnitude"],
            required=False,
            default=None,
            help="Choice to extract the gradient of the input field.",
        )

    def average_args(self):
        """Add arguments for extracting averages."""
        self.parser.add_argument(
            "--fields",
            type=str,
            nargs="+",
            required=True,
            default=None,
            help="Names of the data fields to extract.",
        )
        self.parser.add_argument(
            "--name",
            type=str,
            required=False,
            default="average_data",
            help="Name of the output data file (.pkl).",
        )
        self.parser.add_argument(
            "--normal",
            type=str,
            choices=["x", "y", "z"],
            required=False,
            default=None,
            help="Option to perform 2D slice (defaults to domain average).",
        )
        self.parser.add_argument(
            "--location",
            type=float,
            required=False,
            default=None,
            help="Physical location to perform the 2D slice (if normal is defined).",
        )
        self.parser.add_argument(
            "--rm_eb",
            required=False,
            action="store_true",
            help="Flag to explicitly remove all data in EB regions.",
        )

        # remove potentially conflicting arguments from base class
        self.remove_arg("field")

    def grid_args(self):
        """Add arguments for extracting grid info."""
        self.parser.add_argument(
            "--name",
            type=str,
            required=False,
            default="average_data",
            help="Name of the output data file (.pkl).",
        )

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
        self.parser.add_argument(
            "--fields",
            type=str,
            nargs="+",
            required=True,
            default=None,
            help="Names of the data fields to plot.",
        )
        self.parser.add_argument(
            "-f",
            "--fname",
            type=str,
            nargs="+",
            required=True,
            default="average_data",
            help="Name of the data file to load and plot (.pkl).",
        )
        self.parser.add_argument(
            "--dpi",
            type=int,
            required=False,
            default=300,
            help="dpi of the output image (default = 300).",
        )

        # remove potentially conflicting arguments from base class
        self.remove_arg("field")

    def grid_args(self):
        """Add arguments for plotting grid info."""
        self.parser.add_argument(
            "-f",
            "--fname",
            type=str,
            required=True,
            default="grid_info",
            help="Name of the data file to load and plot (.pkl).",
        )
        self.parser.add_argument(
            "--dpi",
            type=int,
            required=False,
            default=300,
            help="dpi of the output image (default = 300).",
        )
        self.parser.add_argument(
            "--ptype",
            type=str,
            required=False,
            choices=["line", "pie", "bar"],
            default="line",
            help="type of plot to make.",
        )

        # remove potentially conflicting arguments from base class
        self.remove_arg("field")


class ytAnalysisArgs(ytArgs):
    """Class to interface with custom data analysis functions."""

    def __init__(self, **kwargs):
        """Initialize ytAnalysisArgs."""
        super(ytAnalysisArgs, self).__init__(**kwargs)

    def mixture_fraction(self):
        """Add in arguments for analyzing mixture fraction data."""
        self.parser.add_argument(
            "--name",
            type=str,
            required=False,
            default="mixture_average",
            help="Name of the output data file (.pkl).",
        )
        self.parser.add_argument(
            "--rm_eb",
            required=False,
            action="store_true",
            help="Flag to explicitly remove all data in EB regions.",
        )
        self.parser.add_argument(
            "--nbins",
            required=False,
            type=int,
            default=10,
            help="Number of bins to use for the mixture fraction averaging.",
        )
        # self.parser.add_argument(
        #     "--bin_rang",
        #     required=False,
        #     default=[]
        # )
        # remove potentially conflicting arguments from base class
        self.remove_arg("field")
