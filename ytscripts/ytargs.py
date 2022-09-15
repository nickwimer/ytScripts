"""Argument Parser classes for common arguments."""
import argparse


class ytArgs:
    """Base class with standard inputs for yt scripts."""

    def __init__(self):
        """Initialize ytArgs."""
        self.parser = argparse.ArgumentParser()

        self.io_args()

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

    def parse_args(self):
        """Return the parsed args."""
        return self.parser.parse_args()


class ytVisArgs(ytArgs):
    """Class to interface with standard yt visualization functions."""

    def __init__(self, **kwargs):
        """Initialize ytVisArgs."""
        super(ytVisArgs, self).__init__(**kwargs)

    def slice_args(self):
        """Add arguments for slice plots."""
        self.parser.add_argument(
            "--normal",
            type=str,
            required=True,
            help="Normal direction for the slice plot.",
        )
        self.parser.add_argument(
            "-c",
            "--center",
            nargs="+",
            type=float,
            required=False,
            help="Coordinate list for center of slice plot.",
        )
        self.parser.add_argument(
            "--cmap",
            type=str,
            required=False,
            default="dusk",
            help="Colormap for the 2D plot.",
        )
        self.parser.add_argument(
            "--plot_log",
            action="store_true",
            help="Plot in log values.",
        )
        self.parser.add_argument(
            "--grids",
            action="store_true",
            help="Flag to turn on grid annotation.",
        )
        self.parser.add_argument(
            "--grid_offset",
            type=float,
            required=False,
            default=0.0,
            help="Amount to offset center to avoid grid alignment vis issues.",
        )
        self.parser.add_argument(
            "--buff",
            type=int,
            nargs="+",
            required=False,
            default=None,
            help="Buffer for the sliceplot image for plotting.",
        )
        self.parser.add_argument(
            "--dpi",
            type=int,
            required=False,
            default=300,
            help="dpi of the output image (default = 300).",
        )
        self.parser.add_argument(
            "--fbounds",
            type=float,
            nargs="+",
            required=False,
            default=None,
            help="Bounds for the colorbar.",
        )
        self.parser.add_argument(
            "--pbox",
            type=float,
            nargs="+",
            required=False,
            default=None,
            help="Bounding box of the plot specified by the two corners (x0 y0 x1 y1).",
        )


class ytExtractArgs(ytArgs):
    """Class to interface with custom data extraction functions."""

    def __init__(self, **kwargs):
        """Initialize ytExtractArgs."""
        super(ytExtractArgs, self).__init__(**kwargs)

    def slice_args(self):
        """Add arguments for extract slices routine."""
        self.parser.add_argument(
            "--normal",
            type=str,
            required=True,
            help="Direction to perform the slices.",
        )
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
