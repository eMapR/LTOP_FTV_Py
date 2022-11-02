Perform image stabilization using LTOP outputs 
==============================================

This is a step by step guide to the process of generating temporally stabilized imagery using the LandTrendr algorithm and associated LTOP param selection workflow.
This workflow is set up specifically for temporal composites that were created by the NASA SERVIR group from the Mekong hub, however, the general workflow could
be applied to base medoid composites or other temporal composites from other areas. Note also that similar outputs can be generated directly from LandTrendr 
outputs and are default produced as FTV or Fit bands (from GEE LandTrendr Fit) when running either of those versions of the LandTrendr algorithm. 
This particular version of the temporal stabilization also relies on the LandTrendr Optimization workflow (LTOP) which is available on GitHub. This workflow 
and assoicated scripts are also available via GitHub.

The theory here is basically to take LandTrendr breakpoint/vertex years and use the associated regression lines to impose or adjust spectral values of the 
input composite time series to each segment of the LandTrendr-derived regression lines. This results in a time series of temporally stabilized images with 
adjusted spectral values. The process also has the benefit of interpolating some of the missing values in the time series and can have a positive impact on the 
SLC-off error that is frequently encountered when working with imagery from Landsat 7 in the years between 2003 and 2012. The process does not always improve 
this artifact but has been shown to have positive impacts in some areas. Some additional information on this process is available in the associated Google Slides.

**SETUP**
Like the LTOP workflow, this is now set up to accept arguments from the config.yml file that is used as the basis for the LTOP inputs. Running the `create_stabilized_comps.py <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/create_stabilized_comps.py>`_ 
script will generate a task in your GEE account for each year in the time series. This is defined by the startYear and endYear args in the config.yml file. running this stabilization script requires
the `ltop modules <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/ltop.py>`_ and the `config.yml <>`

The first step is to take the outputs of the LTOP workflow and using those with the input time series (in this case SERVIR composites), run LandTrendr Fit to 
generate temporally stabilized values. To run this you need some of the items created with the LTOP workflow. Description of what these things are, the step 
in the LTOP workflow where they are derived and some of their derivation logic are all outlined below. 

LTOP outputs/stabilization inputs:     

cluster_image: ee.Image()
    This is the output of the kmeans algorithm used to spatially constrain the different versions of LandTrendr used in the LTOP process. 
    This is the second step in the LTOP workflow. Note that if you have the run_times argument set to single this will look for a specific kmeans output. If you have that
    argument set to 'multiple' it will look for images containing the KMEANS_imagery string and mosaic those into one image. 

ltop_output: ee.Image()
    This is a multiband image with one band up to the maxObvs param used in the running of LandTrendr. Each band contains LandTrendr breakpoint/vertex
    years. This is the final output of the LTOP workflow. Like with the kmeans outputs, if you have run_times set to 'single' it will look for a specific output in your GEE assets folder. 
    If you have the run_times arg set to 'multiple' it will attempt to construct a mosaicked image.   

table: ee.FeatureCollection()
    These are the versions of LandTrendr that were selected based on the weighted scoring scheme that is implemented between LTOP step 04 and 05. Like with the two 
    previous args, these will be constructed from a list of featureCollections in the instance of run_times being set to 'multiple' or it will look for a single input if run_times = 'single'.     

aoi: ee.Geometry()
    This may change in future versions but currently (11/2/2022), the user needs to specify the aoi as a geometry in the script. If you have a featureCollection just 
    convert to geometry (.geometry()) before passing to the main() function. This is constructed in this way because the YAML file by default passes args as strings. This 
    could be parsed/cast to a geometry object but in the case that you want to add a filter it makes it more challenging to paramaterize externally. 

Make sure the assetsRoot and assetsChild as well as place are all set the same as for your LTOP run or you will hit an error. Make sure your destination folder (assetsChild) has enough space.
If you are running something like a full SE Asia area you will generate hundreds of GBs of data and it will take days to run. 

If you would like to generate an imageCollection from the directory of assets you can use something like below in a separate script.

``var yr_images = []; for (var y = 1990;y < 2022; y++){ var im = ee.Image("projects/servir-mekong/composites/" + y.toString()); yr_images.push(im); }``