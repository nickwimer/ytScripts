"""Argument Parser classes for common arguments."""
import argparse
import json


def write_args(args, file):
    """Write arguments to file."""
    with open(file, "w") as f:
        json.dump(args.__dict__, f, indent=2)


class blenderArgs:
    """Base class with standard inputs for blender scripts."""

    def __init__(self):
        """Initialize blenderArgs."""
        self.parser = argparse.ArgumentParser()

        self.io_args()
        self.camera_args()
        self.light_args()
        self.material_args()

    def parse_args(self):
        """Return the parsed args."""
        return self.parser.parse_args()

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
            "--ftype",
            type=str,
            required=True,
            default=None,
            help="File type for the input data.",
        )
        self.parser.add_argument(
            "-f",
            "--fname",
            type=str,
            required=True,
            action="append",
            default=None,
            help="Name of file to load and render.",
        )
        self.parser.add_argument(
            "--oname",
            type=str,
            required=False,
            default=None,
            help="Name of output blender file to save.",
        )

    def camera_args(self):
        """Arguments to define camera settings."""
        self.parser.add_argument(
            "--cloc",
            type=float,
            nargs="+",
            required=False,
            default=None,
            help="X Y Z coordinates for the camera location.",
        )
        self.parser.add_argument(
            "--crot",
            type=float,
            nargs="+",
            required=False,
            default=None,
            help="X Y Z coordinates for the camera rotation (degrees).",
        )

    def light_args(self):
        """Arguments to define light settings."""
        self.parser.add_argument(
            "--lloc",
            type=float,
            nargs="+",
            required=False,
            default=None,
            help="X Y Z coordinates for the light location.",
        )
        self.parser.add_argument(
            "--lrot",
            type=float,
            nargs="+",
            required=False,
            default=None,
            help="X Y Z coordinates for the light rotation (degrees).",
        )
        self.parser.add_argument(
            "--energy",
            type=float,
            required=False,
            default=100,
            help="Power output of the light source.",
        )
        self.parser.add_argument(
            "--ltype",
            type=str,
            required=False,
            choices=["POINT", "SUN", "SPOT"],
            default="POINT",
            help="Light source type.",
        )

    def material_args(self):
        self.parser.add_argument(
            "--material",
            type=str,
            nargs="+",
            choices=["metal", "default"],
            required=False,
            default=None,
            help="List of materials corresponding to objects loaded.",
        )
