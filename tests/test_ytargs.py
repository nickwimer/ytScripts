"""Tests for parsing arguments and merging them with an --ifile input file."""

import pytest

import ytscripts.ytargs as ytargs

# Every script needs --datapath; the parser only checks that it is set
DATA = ["--datapath", "."]


def write_toml(tmp_path, text):
    """Write an input file and return its path."""
    path = tmp_path / "input.toml"
    path.write_text(text)
    return str(path)


def slice_plot_parser():
    """Build the parser used by quick_vis/slice_plot.py."""
    parser = ytargs.ytVisArgs()
    parser.orientation_args()
    parser.vis_2d_args()
    parser.slice_args()
    return parser


def extract_slices_parser():
    """Build the parser used by data_extraction/extract_slices.py."""
    parser = ytargs.ytExtractArgs()
    parser.orientation_args()
    parser.slice_args()
    return parser


def isosurface_parser():
    """Build the parser used by data_extraction/extract_isosurfaces.py."""
    parser = ytargs.ytExtractArgs()
    parser.isosurface_args()
    return parser


def test_command_line_only():
    args = slice_plot_parser().get_args([*DATA, "--field", "density", "--dpi", "150"])
    assert args["field"] == "density"
    assert args["dpi"] == 150
    assert args["normal"] == "z"


def test_input_file_fills_in_values(tmp_path):
    ifile = write_toml(
        tmp_path,
        'title = "plot"\nfield = "temp"\nnormal = "x"\npbox = [-1, -1, 1, 1]\n',
    )
    args = slice_plot_parser().get_args([*DATA, "--ifile", ifile])
    assert args["field"] == "temp"
    assert args["normal"] == "x"
    assert args["pbox"] == [-1, -1, 1, 1]
    assert "title" not in args


def test_command_line_wins_over_input_file(tmp_path):
    ifile = write_toml(
        tmp_path, 'field = "temp"\nnormal = "x"\ndpi = 100\nfbounds = [0, 1]\n'
    )
    args = slice_plot_parser().get_args(
        [
            *DATA,
            "--ifile",
            ifile,
            "--normal",
            "y",
            "--dpi",
            "150",
            "--fbounds",
            "0.5",
            "2",
        ]
    )
    assert args["field"] == "temp"
    assert args["normal"] == "y"
    assert args["dpi"] == 150
    assert args["fbounds"] == [0.5, 2.0]


def test_negative_numbers_with_input_file(tmp_path):
    ifile = write_toml(tmp_path, 'field = "temp"\n')
    # argparse only reads -1 or -0.5 style values as negative numbers, so scientific
    # notation needs the --option=value form
    args = slice_plot_parser().get_args(
        [*DATA, "--ifile", ifile, "--pbox", "-1", "-2", "1", "2", "--grid_offset=-1e-6"]
    )
    assert args["pbox"] == [-1.0, -2.0, 1.0, 2.0]
    assert args["grid_offset"] == -1e-6


def test_single_value_for_list_option_becomes_a_list(tmp_path):
    ifile = write_toml(tmp_path, 'pname = "plt00100"\nclw = 2\n')
    args = slice_plot_parser().get_args([*DATA, "--ifile", ifile])
    assert args["pname"] == ["plt00100"]
    assert args["clw"] == [2]

    args = slice_plot_parser().get_args(
        [*DATA, "--ifile", ifile, "--pname", "plt00200"]
    )
    assert args["pname"] == ["plt00200"]


def test_flags_from_input_file_and_command_line(tmp_path):
    ifile = write_toml(tmp_path, "no_time = true\n")
    args = slice_plot_parser().get_args([*DATA, "--ifile", ifile, "--no_units"])
    assert args["no_time"] is True
    assert args["no_units"] is True


def test_unknown_option_in_input_file_is_ignored(tmp_path, capsys):
    ifile = write_toml(tmp_path, 'field = "temp"\nfeild = "oops"\n')
    args = slice_plot_parser().get_args([*DATA, "--ifile", ifile])
    assert "feild" not in args
    assert "feild" in capsys.readouterr().out


def test_override_args_reuses_the_parsed_list(tmp_path):
    """Overrides come from the list given to parse_args, not from sys.argv."""
    ifile = write_toml(tmp_path, 'field = "temp"\nnormal = "z"\n')
    parser = slice_plot_parser()
    init_args = parser.parse_args([*DATA, "--normal", "y", "--ifile", ifile])
    args = parser.override_args(init_args, ifile)
    assert args["normal"] == "y"
    assert args["field"] == "temp"


def test_required_values_can_come_from_input_file(tmp_path):
    ifile = write_toml(tmp_path, "min = 0.0\nmax = 1.0\nnum_slices = 4\n")
    args = extract_slices_parser().get_args([*DATA, "--ifile", ifile])
    assert (args["min"], args["max"], args["num_slices"]) == (0.0, 1.0, 4)


def test_missing_required_value_is_an_error(tmp_path, capsys):
    ifile = write_toml(tmp_path, "min = 0.0\nmax = 1.0\n")
    with pytest.raises(SystemExit) as err:
        extract_slices_parser().get_args([*DATA, "--ifile", ifile])
    assert err.value.code == 2
    assert "--num_slices" in capsys.readouterr().err

    with pytest.raises(SystemExit):
        extract_slices_parser().get_args([*DATA, "--min", "0", "--max", "1"])


def test_isosurface_value_of_zero():
    assert isosurface_parser().get_args([*DATA, "--value", "0"])["value"] == 0.0


def test_isosurface_value_from_input_file(tmp_path):
    ifile = write_toml(tmp_path, "value = 0.5\n")
    assert isosurface_parser().get_args([*DATA, "--ifile", ifile])["value"] == 0.5


def test_isosurface_needs_value_or_vfunction(capsys):
    with pytest.raises(SystemExit):
        isosurface_parser().get_args(
            [
                *DATA,
            ]
        )
    assert "--value or --vfunction" in capsys.readouterr().err

    with pytest.raises(SystemExit):
        isosurface_parser().get_args(
            [*DATA, "--value", "1", "--vfunction", "0", "1", "2", "3"]
        )


def test_removed_field_option_is_not_required():
    parser = ytargs.ytExtractArgs()
    parser.average_args()
    args = parser.get_args([*DATA, "--fields", "temp"])
    assert "field" not in args
    assert args["fields"] == ["temp"]


def test_plot_averages_default_file_name_is_a_list():
    parser = ytargs.ytPlotArgs()
    parser.average_args()
    assert parser.get_args([*DATA, "--fields", "temp"])["fname"] == ["average_data"]


def test_required_options_say_so_in_help():
    help_text = extract_slices_parser().get_parser().format_help()
    assert "(required)" in help_text


def average_parser():
    """Build the parser used by data_extraction/extract_averages.py."""
    parser = ytargs.ytExtractArgs()
    parser.average_args()
    return parser


@pytest.mark.parametrize(
    "given, kept", [("x", "x"), ("xz", "xz"), ("x+z", "xz"), ("x-z", "x-z")]
)
def test_normal_takes_axes_and_diagonals(given, kept):
    assert slice_plot_parser().get_args([*DATA, "--normal", given])["normal"] == kept
    args = extract_slices_parser().get_args(
        [*DATA, "--normal", given, "--min", "0", "--max", "1", "--num_slices", "2"]
    )
    assert args["normal"] == kept
    args = average_parser().get_args(
        [*DATA, "--fields", "temp", "--normal", given, "--location", "1"]
    )
    assert args["normal"] == kept


@pytest.mark.parametrize("bad", ["w", "xx", "xw", "x-", "-x", "xyz"])
def test_bad_normal_is_a_usage_error(bad, capsys):
    with pytest.raises(SystemExit):
        slice_plot_parser().get_args([*DATA, f"--normal={bad}"])
    assert "pair of different axes" in capsys.readouterr().err


@pytest.mark.parametrize("value", ['"xw"', "1"])
def test_normal_from_input_file_is_checked(tmp_path, capsys, value):
    ifile = write_toml(tmp_path, f"normal = {value}\n")
    with pytest.raises(SystemExit):
        slice_plot_parser().get_args([*DATA, "--ifile", ifile])
    assert "--normal" in capsys.readouterr().err


def test_diagonal_normal_from_input_file(tmp_path):
    ifile = write_toml(tmp_path, 'normal = "z+x"\n')
    assert slice_plot_parser().get_args([*DATA, "--ifile", ifile])["normal"] == "zx"


def test_any_up_suits_a_diagonal_normal():
    parser = ytargs.ytVisArgs()
    parser.orientation_args(up=True)
    for up in "xyz":
        args = parser.get_args([*DATA, "--normal", "xz", "--up", up])
        assert (args["normal"], args["up"]) == ("xz", up)
