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
For now, this only extracts along the x direction.

`python data_extraction/extract_slices.py -p DIR/ --field "Y(NC12H26)" --LM --xmin 0.005 --xmax 0.1 --num_slices 16`

This will extract all plot files contained in directory `DIR/` for the field `Y(NC12H26)` consistent with the low Mach units (not really necessary here), making 16 slices starting from x = 0.005 to x = 0.1

These slices will be saved in `outdata/slices/` with the following variables: `time`, `fcoords`, `resolution`, `dimensions`, `left_edge`, `right_edge`, `max_level`, `xloc`, `field`, `var_slice`

## extract_averages.py
Extracts domain averaged quantities and saves in a pickled pandas dataframe

`python data_extraction/extract_averages.py -p DIR/ --pname plt00001 plt00002 --name NAME --fields mag_vort`

Data will be saved under `outdata/averages`


# Scripts for plotting extracted data
Scripts for plotting data that was previously extracted using files under `data_extraction/`


## plot_slices.py
This will load in the numpy data structures contained in the input path and make plots

`python plot_slices.py -p outdata/`

where `outdata` is the directory containing the list of `.npz` files. These images will automatically be saved in `imgpath`


## plot_averages.py
This will load in the pandas dataframe and make time series plots

`python plot_data/plot_averages.py -p outdata/averages/ -f NAME --field mag_vort`

Plots will be saved under `outdata/images/`



# Scripts for Visualization
Scripts for in-place quick visualization are located under `quick_vis`

These scripts are currently provided as examples and will need manual modification. Future updates will make them more automated.


## slice_plot.py
This will take all `plt` files in the input directory and create images down the middle of the domain subject to inputs

`python quick_vis/slice_plot.py -p DIR/ --field "Y(NC12H26)" --normal x --LM --fbounds 0 0.1`

This will create a 2D slice plot with x as the normal irection and bounds on field set to 0 - 0.1 in field units

Helpful options:

`--datapath`: Path to the plot files.

`--outpath`: Path to the output image directory (defualt to datapath/images).

`--pname`: Used to specify individual plot file names instead of doing all files in the datapath.

`--field`: Name of the field for visualization.

`--normal`: Normal direction for the slice plot. Slice will be taken in the middle of the domain.

`-c, --center`: list of floats for center coordinates if different from center specified with `normal`.

`--fbounds`: Bounds for the colormap for the field.

`--cmap`: Name of the colormap for the slice plot (defualts to "dusk").

`--LM`: Flag to specify that the data is in SI units (defualts to cgs).

`--plot_log`: Flag to plot the data using log values.

`--grids`: Flag to turn on the grid annotations.

`--grid_offset`: Float value to offset the center value to avoid grid alignment visualization issues (defualts to no offset).

`--buff`: Buffer resolution for the sliceplot image for plotting.

`--dpi`: dpi of the output image (default = 300).

`--pbox`: Bounding box for the output image specified by the two corners of a rectangle (x0 y0 x1 y1).
