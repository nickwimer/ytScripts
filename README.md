# ytScripts
Collection of Python scripts that use "The yt Project" for data manipulation and visualization

To install dependencies, with a working `conda` distribution, type:

`conda env create --file environment.yml`

to update an existing conda environment:

`conda env update --name ytScripts --file environment.yml --prune`


after environment is created:

`conda activate ytScripts`

All formatting must pass through `black`, `isort`, and `flake8`

The proper order should be `black`, then `isort`, finally `flake8` to catch any issues. If there are further changes, repeat the formatting sequence


# Scripts for Data Extractions
Scripts for data extraction and maniupulation are located under `data_extraction/`


## extract_slices.py
For now, this only extracts along the x direction.

`python extract_slices.py -p DIR/ --field "Y(NC12H26)" --LM --xmin 0.005 --xmax 0.1 --num_slices 16`

This will extract all plot files contained in directory `DIR/` for the field `Y(NC12H26)` consistent with the low Mach units (not really necessary here), making 16 slices starting from x = 0.005 to x = 0.1

These slices will be saved in `outdata` with the following variables: `time`, `fcoords`, `resolution`, `dimensions`, `left_edge`, `right_edge`, `max_level`, `xloc`, `field`, `var_slice`


## plot_slices.py
This will load in the numpy data structures contained in the input path and make plots

`python plot_slices.py -p outdata/`

where `outdata` is the directory containing the list of `.npz` files. These images will automatically be saved in `imgpath`



# Scripts for Visualization
Scripts for in-place quick visualization are located under `quick_vis`

These scripts are currently provided as examples and will need manual modification. Future updates will make them more automated.


## slice_plot.py
This will take all `plt` files in the input directory and create images down the middle of the domain subject to inputs

`python quick_vis/slice_plot.py -p DIR/ --field "Y(NC12H26)" --normal x --LM --fbounds 0 0.1`

This will create a 2D slice plot with x as the normal irection and bounds on field set to 0 - 0.1 in field units

Helpful options:

`--datapath`: Path to the plot files.

`--pname`: Used to specify individual plot file names instead of doing all files in the datapath.

`--normal`: Normal direction for the slice plot. Slice will be taken in the middle of the domain.

`-c, --center`: list of floats for center coordinates if different from center specified with `normal`.

`--fbounds`: Bounds for the colormap for the field.

`--cmap`: Name of the colormap for the slice plot (defualts to "dusk").

`--LM`: Flag to specify that the data is in SI units (defualts to cgs).

`--plot_log`: Flag to plot the data using log values.

`--grids`: Flag to turn on the grid annotations.

`--grid_offset`: Float value to offset the center value to avoid grid alignment visualization issues (defualts to no offset).

