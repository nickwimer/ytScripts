Welcome to ytScripts's documentation!
=====================================

ytScripts is a collection of scripts targeted for analyzing data from simulations run
with AMReX-based codes such as the Pele Suite. The codes can be run using the python
scripts within each of the sub-directories targeting specific tasks such as quick
visualization, data extraction, data_analysis, and plotting. Each of the scripts can
take inputs from the command line or through the use of TOML files. If the scripts are
installed through pip, they can be run from anywhere on the command line through the
new entry points.

The entry points currently supported are:

- quick_vis
- data_extraction
- plot_data

More documentation is coming soon! For now, please refer to the README for more
information on installation and check the individual subpackages for usage.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quick_vis
   data_extraction
   plot_data
   ytscripts
   udfs


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
