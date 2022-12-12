.. LTOP_py_docs documentation master file, created by
   sphinx-quickstart on Wed Oct 19 15:46:22 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Documentation for LandTrendr Optimization (LTOP)
========================================

.. image:: images/LT_logo.jpg

The LandTrendr algorithm is a temporal segmentation algorithm built mostly for the Lansat image archive. It can be used for change detection analysis and temporal stabilization/homogenization 
of image time series. One issue with the LandTrendr algorithm is that it can be paramaterized in different ways depending on the target land cover/land change class(es) and the 
biophysical changes you are interested in. To address this challenge, the LandTrendr Optimization (LTOP) workflow provides an automated means of selecting different versions of LandTrendr that are 
more appropriate to specific geographic areas. The process relies on the Google Earth Engine Python API and Google Cloud Serivice (GCS) cloud projects/buckets. 

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   LTOP theory and background <ltop_background.rst>
   Setup LTOP runs <general_setup.rst>
   List of scripts <scripts_list.rst>
   LTOP paramaters <config.rst>
   Example run <examples.rst>
   Information on LTOP steps <ltop_steps.rst>
   LTOP testing <testing.rst>
   Image stabilization <stabilization.rst>
   Change detection <change_detection.rst>
   

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
