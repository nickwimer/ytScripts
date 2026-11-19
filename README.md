# ytScripts

Collection of Python scripts that use "The yt Project" for data manipulation and visualization

## Installation

Installation can be handled in one of two ways. The new, recommended method which will allow
for more native command line usage is to install the entire repo as a python package using `pip`.
This is achieved using the following steps:

```shell
conda create -n ytscripts
conda activate ytscripts
conda install python=3.11
```

The pip package can then be installed either:

```shell
git clone https://github.com/nickwimer/ytScripts.git
cd ytScripts
pip install --upgrade .
```

or directly through github:

```shell
pip install --upgrade git+https://github.com/nickwimer/ytScripts.git
```

NOTE: `mpi4py` is only needed to run in parallel with `mpirun` or `srun`, so the pip install
leaves it out. To run in parallel, install it as well with `pip install --upgrade ".[mpi]"`
(or `pip install mpi4py`). It builds against the MPI libraries it finds, which must be the
same MPI you launch with: on a cluster, load the MPI module first, both before installing
and before running.

---

The older method of installing is to use the `environment.yml` file to create the conda environment:

To install dependencies, with a working `conda` distribution, type:

`conda env create --file environment.yml`

to update an existing conda environment:

`conda env update --name ytscripts --file environment.yml --prune`

after environment is created:

`conda activate ytscripts`

NOTE: Most scripts can now make full use of parallel processing either over multiple datasets in a time series or through domain decomposition (depending on the application). Just submit using `mpirun -np X` (or system equivalent). This is particularly useful when dealing with a large number of time outputs or with very large data.

MPI is only started when a script is launched that way, with more than one process. A plain `python script.py` run never touches MPI and does not need `mpi4py`. `--no_mpi` keeps MPI off even under `mpirun` or `srun`.

## Documentation

Documentation is provided through Sphinx under Docs. Everything necessary to build the documentation is provided in the `environment.yml` file.

Simply navigate to `Docs/`:
`cd Docs/`

and do `make html` to build the docs.

Then `open Docs/build/html/index.html`

Following is a summary of the scripts provided, but this information will be removed in a future update in support for the github docs...

## Contributing

All formatting must pass through `black`, `isort`, and `flake8`

The proper order should be `black`, then `isort`, finally `flake8` to catch any issues. If there are further changes, repeat the formatting sequence

---

---

# Choosing plotfiles

Every script that reads plotfiles takes `--datapath`, the folder holding them, and optionally `--pname` to pick some of them:

- Without `--pname`, every plotfile named `plt` followed by digits (`plt00100`, `plt01264`, ...) is used. Other plotfiles a run writes alongside, such as `pltU00100` or `plt00100.old.4821`, are left out.
- With `--pname`, any name works: give plotfile names or quoted patterns inside `--datapath`, e.g. `--pname pltReact01264` or `--pname "pltReact*"`. `--pname` takes names, not paths; the folder goes after `--datapath`.
- Plotfiles are taken in order of the number at the end of their names, and output images are numbered by each plotfile's place in its series, so frames stay consecutive for making movies.

# Scripts for Data Extractions

Scripts for data extraction and manipulation are located under `data_extraction/`

## extract_slices.py

Extracts 2D slices along specified normal and saves to a npz for later analysis.

Ex: `python data_extraction/extract_slices.py --datapath DATA_DIR/ --field "Y(NC12H26)" --normal x --min 0.005 --max 0.1 --num_slices 16`

This will extract all plot files contained in directory `DATA_DIR/` for the field `Y(NC12H26)`, making 16 slices starting from x = 0.005 to x = 0.1

`--normal` also takes a diagonal, as for [slice_plot.py](#slice_plotpy): `--normal xz` cuts planes normal to (1, 0, 1), and `--min`/`--max` are then distances from the origin along the unit normal, so each plane is (x + z)/√2 = d. Every plane must cut through the domain, strictly between the smallest and largest (x + z)/√2 in it; this is checked before any plotfile is read. Each diagonal slice covers the part of its plane inside the domain at one pixel per finest cell, with the same orientation as in `slice_plot.py` (y up and (x − z)/√2 across for `xz`).

These slices will be saved in `outdata/slices/` with the following variables: `fcoords`, `normal`, `iloc`, `fields`, `slices`, and `ds_attributes` which contains all attributes specified in `utilities.py/get_attributes()`. Diagonal slices also hold `normal_vector`, `across` and `up` (unit vectors), `center` (the middle of the image), `bounds` (across_min, across_max, up_min, up_max as offsets from `center`) and the axis `labels`.

`python data_extraction/extract_slices.py --help` for full list of arguments.

## extract_averages.py

Extracts domain averaged quantities and saves in a pickled Pandas DataFrame.

The default behavior is to perform a full domain average of the quantity, but 2D averages can be extracted over slices specified with a `normal` direction and corresponding `location` keyword. With a diagonal `normal` such as `xz`, the slice is the plane normal to (1, 0, 1) at distance `location` from the origin along the unit normal.

NOTE: If you have EB boundaries in the domain, you should run with flag `--rm_eb` to remove the non-fluid regions from the averages.

Ex: `python data_extraction/extract_averages.py --datapath DIR/ --pname plt00001 plt00002 --name NAME --fields mag_vort`

Data will be saved under `outdata/averages`, unless otherwise specified.

`python data_extraction/extract_averages.py --help` for full list of arguments.

## extract_isosurfaces.py

Extracts an isosurface of specified field and value and saves to file for visualization in external program (such as ParaView or Blender).

Ex: `python data_extraction/extract_isosurfaces.py --datapath DATADIR/ --pname plt00001 --field magvort --value 50000.0 --format xdmf`

Output formats are `ply`, `obj`, `hdf5`/`xdmf`.

Isosurface file will be saved under `outdata/isosurfaces`.

Can be run in parallel with `mpirun` or `srun` (needs `mpi4py`). Should run with `--do_ghost` if there are holes in the iso-surfaces: it adds a layer of ghost cells around each grid, which closes the cracks between neighboring grids at the same refinement level. Small cracks can remain where the surface crosses from one refinement level to another.

Can use `--yt` to compare the built in iso-surface extraction with the custom version. `yt` version is not parallelized.

With the `hdf5`/`xdmf` formats, `--extra_fields` stores other fields on the surface so it can be colored by them, e.g. `--extra_fields temp Y(O2)`. Each is interpolated to the surface vertices from the same grid the surface was built from.

`python data_extraction/extract_isosurfaces.py --help` for full list of arguments.

## extract_grid_info.py

Extracts grid information at each level and saves to file.

Ex: `python data_extraction/extract_grid_info.py --datapath DATADIR/ --outpath OUTDIR/ --name FILE_NAME`

Will save a pickle file of the Pandas DataFrame with grid information as a function of time and some stored metadata about the simulation.

## extract_lines.py

Extracts a line of data along x, y, z or a diagonal through every plot file, through the finest cells at each point.

Ex: `python data_extraction/extract_lines.py --datapath DATADIR/ --field temp --normal x --coords 0.01 0.01 --name FILE_NAME`

`--coords` places the line in the other two directions: (y, z) for a line along x, (z, x) along y, and (x, y) along z.

For a diagonal line, `--normal` takes a pair of axes as for [slice_plot.py](#slice_plotpy), such as `xz` for (1, 0, 1) or `x-z` for (1, 0, −1), and `--coords` takes a point (x, y, z) on the line, e.g. `--normal xz --coords 0 0.01 0`. The line runs through the whole domain, and its positions are the distance from the origin along the unit direction, (x + z)/√2 for `xz`.

Saves a pickle file of a Pandas DataFrame under `outdata/lines` (or `--outpath`), indexed by position along the line with one column per time. With AMR the cells along the line can change over time, so the index holds every position seen and a time has NaN where it has no cell; `df.interpolate(method="index")` fills those in if needed. The field, coordinates and units are kept in `df.attrs`.

# Scripts for plotting extracted data

Scripts for plotting data that was previously extracted using files under `data_extraction/`

## plot_slices.py

This will load in the NumPy data structures contained in the input path and make plots.

Ex: `python plot_data/plot_slices.py --datapath outdata/ --field magvort`

where `outdata` is the directory containing the list of `.npz` files. These images will automatically be saved in `imgpath`.

Diagonal slices from `extract_slices.py --normal xz` are drawn with the directions saved with them, e.g. (x − z)/√2 across and y up, measured from the middle of the slice; `--pbox` then takes those offsets.

`python plot_data/plot_slices.py --help` for full list of arguments.

### To Do:

- [ ] Add in various EB visualization options in quick vis slice plot

## plot_averages.py

This will load in the Pandas DataFrame and make time series plots

Ex: `python plot_data/plot_averages.py --datapath outdata/averages/ --fname NAME --fields mag_vort`

Plots will be saved under `outdata/images/`

`python plot_data/plot_averages.py --help` for full list of arguments.

## plot_grid_info.py

Load grid info data from pickled Pandas DataFrame and make simple plot as an example.

`python plot_data/plot_grid_info.py --datapath DATADIR/ --outpath OUTDIR/ --fname FILENAME`

# Scripts for Visualization

Scripts for in-place quick visualization are located under `quick_vis`

These scripts are currently provided as examples and will need manual modification. Future updates will make them more automated.

## slice_plot.py

This will take all `plt` files in the input directory and create 2D images subject to inputs

Ex: `python quick_vis/slice_plot.py --datapath DATA_DIR/ --field "Y(NC12H26)" --normal x --fbounds 0 0.1`

This will create a 2D slice plot with x as the normal direction and bounds on field set to 0 - 0.1 in field units

`python quick_vis/slice_plot.py --help` for full list of options.

Can now make full use of parallel processing over multiple datasets in a time series. Just submit using `mpirun -np X` or equivalent and images will be processed in an embarrassingly parallel manner.

This script now automatically references a list of configuration settings located in `quick_vis/config.toml`. If you would like to change any of these default settings simply create a new configuration file called `quick_vis/config_user.toml` and manually override just the settings that you want to change. The code will update the configuration settings with your new values. NOTE: In the future many of the command line options will be incorporated into these files.

Some helpful options:

`--datapath`: Path to the folder holding the plot files (required).

`--outpath`: Path to the output image directory (defaults to `outdata/images` in the ytScripts folder).

`--pname`: Plot file names or quoted patterns inside `--datapath`, instead of every `plt<digits>` plot file there; any name works (see [Choosing plotfiles](#choosing-plotfiles)).

`--field`: Name of the field for visualization.

`--normal`: Normal direction for the slice plot. Slice will be taken in the middle of the domain. The image shows y across and z up for `--normal x`, x across and z up for `--normal y`, and x across and y up for `--normal z`.

`--normal` also takes a diagonal: a pair of axes such as `xz` for the plane normal to (1, 0, 1) (also `xy` and `yz`; `x+z` and `zx` are the same as `xz`), or a signed pair such as `x-z` for (1, 0, −1). By default the axis not in the pair points up, and across is up × normal: `--normal xz` draws (x − z)/√2 across and y up, and `--normal z-x` draws (x + z)/√2 across and y up. The image covers the part of the plane inside the domain, and its axes are offsets from the slice center (the middle of the domain, or `--center`) along those directions. For example:

`python quick_vis/slice_plot.py --datapath DATA_DIR/ --field HeatRelease --normal xz --fbounds 1e9 5e9`

`--up`: Axis pointing up in the image, one of the two axes in the slice. For example, `--normal x --up y` draws z across and y up, which suits flow along +y. Without it, the image keeps the orientation given under `--normal`. An `--up` along `--normal` is an error. For a diagonal normal, an axis in the pair is tilted into the plane, so `--normal xz --up x` draws (x − z)/√2 up and −y across.

`-c, --center`: list of floats for center coordinates if different from center specified with `normal`.

`--fbounds`: Bounds for the colormap for the field.

`--cmap`: Name of the colormap for the slice plot (defualts to "dusk").

`--SI`: Flag to specify that the data is in SI units (defaults to cgs).

`--plot_log`: Flag to plot the data using log values.

`--grids`: Flag to turn on the grid annotations. yt cannot draw them on diagonal slices, so there it prints a warning and is skipped.

`--cells`: Draw the cell edges, given as (linewidth alpha color). yt draws them at the wrong size on diagonal slices, so there it prints a warning and is skipped.

`--grid_offset`: Float value to offset the center value to avoid grid alignment visualization issues (defaults to no offset).

`--buff`: Buffer resolution for the sliceplot image for plotting, in pixels across and up. Defaults to one pixel per finest cell (for a diagonal slice, per the smallest finest cell along the axes each image direction runs through). Where yt has to swap the image axes (`--normal y` unless `--up x`, `--normal x --up y` and `--normal z --up x`), the buffer is made square at the larger of the two, because yt draws only part of a swapped image otherwise.

`--dpi`: dpi of the output image (default = 300).

`--pbox`: Bounding box for the output image specified by the two corners of a rectangle (x0 y0 x1 y1), as positions across and up the image: (y0 z0 y1 z1) for `--normal x`, (x0 z0 x1 z1) for `--normal y` and (x0 y0 x1 y1) for `--normal z`. It follows `--up`, so `--normal x --up y` takes (z0 y0 z1 y1). For a diagonal normal the corners are offsets from the slice center across and up the image, e.g. (a0 y0 a1 y1) with a = (x − z)/√2 for `--normal xz`.

`--contour`: Plot a contour line (color=`COLOR`) of `FIELD` with `VALUE` on top of 2D slice. Specified like: `--contour FIELD VALUE COLOR`.

`--clw`: Sets the linewidth of the contour lines. Must be same length as the number of contour lines specified with `--contour`.

`--pickle`: Optional flag to dump the image as a pickle file for later manipulation/customization.

`--grid_info`: Add a text box to the slice plot with information about the grids in the simulation. Inputs are: `xloc`, `yloc`, `min_level`, and `max_level`, where the first two inputs define the location of the text box (positions across and up the image, in its axis units, so they follow `--up` like `--pbox`) and the second two inputs define the level range for information in the text box.

`--rm_eb`: Optional flag to remove the EB boundary from the plot as defined by `vfrac` field in the dataset. Takes a float to specify the color between `[0=white, 1=black]`.

`--gradient`: Choice of ["x", "y", "z", "magnitude"] to compute and visualize the gradient of the input field

`--no_time`: Flag to remove the timestamp in the figure

`--no_units`: Flag to remove all units from the plots (axes and colorbar)

`--use_tex`: Flag to render the plot text with LaTeX. Off by default: it needs a working TeX installation and is slower, and a broken one can make the script wait forever with no error. Labels such as `$\rho$` render without it.
