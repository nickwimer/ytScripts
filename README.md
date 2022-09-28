# ytScripts
Collection of Python scripts that use "The yt Project" for data manipulation and visualization

To install dependencies, with a working `conda` distribution, type:

`conda env create --file environment.yml`

to update an existing conda environment:

`conda env update --name ytscripts --file environment.yml --prune`


after environment is created:

`conda activate ytscripts`

All formatting must pass through `black`, `isort`, and `flake8`

The proper order should be `black`, then `isort`, finally `flake8` to catch any issues. If there are further changes, repeat the formatting sequence


# Scripts for Data Extractions
Scripts for data extraction and maniupulation are located under `data_extraction/`


## extract_slices.py
Extracts 2D slices along specified normal and saves to a npz for later analysis.

Ex: `python data_extraction/extract_slices.py -p DATA_DIR/ --field "Y(NC12H26)" --normal x --min 0.005 --max 0.1 --num_slices 16`

This will extract all plot files contained in directory `DATA_DIR/` for the field `Y(NC12H26)`, making 16 slices starting from x = 0.005 to x = 0.1

These slices will be saved in `outdata/slices/` with the following variables: `fcoords`, `normal`, `iloc`, `fields`, `slices`, and `ds_attributes` which contains all attributes specified in `utilities.py/get_attributes()`.

`python data_extraction/extract_slices.py --help` for full list of arguments.

## extract_averages.py
Extracts domain averaged quantities and saves in a pickled pandas dataframe

Ex: `python data_extraction/extract_averages.py -p DIR/ --pname plt00001 plt00002 --name NAME --fields mag_vort`

Data will be saved under `outdata/averages`.

`python data_extraction/extract_averages.py --help` for full list of arguments.


## extract_isosurfaces.ppy
Extracts an isosurface of specified field and value and saves to file for visualization in external program (such as ParaView or Blender).

Ex: `python data_extraction/extract_isosurfaces.py -p DATADIR/ --pname plt00001 --field magvort --value 50000.0 --format xdmf`

Output formats are `ply`, `obj`, `hdf5`/`xdmf`.

Isosurface file will be saved under `outdata/isosurfaces`.

Can be run in parallel with `mpi4py`. Should run with `--do_ghost` if there are holes in the iso-surfaces.

Can use `--yt` to compare the built in iso-surface extraction with the custom version. `yt` version is not parallelized.

`python data_extraction/extract_isosurfaces.py --help` for full list of arguments.


# Scripts for plotting extracted data
Scripts for plotting data that was previously extracted using files under `data_extraction/`


## plot_slices.py
This will load in the numpy data structures contained in the input path and make plots.

Ex: `python plot_data/plot_slices.py -p outdata/ --field magvort`

where `outdata` is the directory containing the list of `.npz` files. These images will automatically be saved in `imgpath`.

`python plot_data/plot_slices.py --help` for full list of arguments.


## plot_averages.py
This will load in the pandas dataframe and make time series plots

Ex: `python plot_data/plot_averages.py -p outdata/averages/ -f NAME --field mag_vort`

Plots will be saved under `outdata/images/`

`python plot_data/plot_averages.py --help` for full list of arguments.



# Scripts for Visualization
Scripts for in-place quick visualization are located under `quick_vis`

These scripts are currently provided as examples and will need manual modification. Future updates will make them more automated.


## slice_plot.py
This will take all `plt` files in the input directory and create 2D images subject to inputs

Ex: `python quick_vis/slice_plot.py -p DATA_DIR/ --field "Y(NC12H26)" --normal x --fbounds 0 0.1`

This will create a 2D slice plot with x as the normal irection and bounds on field set to 0 - 0.1 in field units

`python quick_vis/slice_plot.py --help` for full list of options.

Can now make full use of parallel processing over multiple datasets in a timeseries. Just submit using `mpirun -np X` or equivalent and images will be processed in an embarassingly parallel manner.

Some helpful options:

`--datapath`: Path to the plot files.

`--outpath`: Path to the output image directory (defualt to datapath/images).

`--pname`: Used to specify individual plot file names instead of doing all files in the datapath.

`--field`: Name of the field for visualization.

`--normal`: Normal direction for the slice plot. Slice will be taken in the middle of the domain.

`-c, --center`: list of floats for center coordinates if different from center specified with `normal`.

`--fbounds`: Bounds for the colormap for the field.

`--cmap`: Name of the colormap for the slice plot (defualts to "dusk").

`--SI`: Flag to specify that the data is in SI units (defualts to cgs).

`--plot_log`: Flag to plot the data using log values.

`--grids`: Flag to turn on the grid annotations.

`--grid_offset`: Float value to offset the center value to avoid grid alignment visualization issues (defualts to no offset).

`--buff`: Buffer resolution for the sliceplot image for plotting.

`--dpi`: dpi of the output image (default = 300).

`--pbox`: Bounding box for the output image specified by the two corners of a rectangle (x0 y0 x1 y1).

`--contour`: Plot a contour line of `FIELD` with `VALUE` on top of 2D slice. Specified like: `--contour FIELD VALUE`.
