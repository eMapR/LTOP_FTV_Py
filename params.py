#  ########################################################################################################
#  # #\\
#  # LandTrendr Optimization Paramater File                           #\\
#  # #\\
#  ########################################################################################################
import ee
# ee.Authenticate() #uncomment after testing
ee.Initialize()

#just use for testing 
geometry = ee.Geometry.Polygon(
        [[[105.75931157311999, 13.350592925813421],
          [105.75931157311999, 13.211590516861936],
          [106.03122319421374, 13.211590516861936],
          [106.03122319421374, 13.350592925813421]]])

#note that its important you set up the place and the imageSource in advance because this will determine
#your naming conventions going forward. 
params = {
    "version": '0.0.2',
    "place": 'cambodia_subset',
    "startYear": 1990,
    "endYear": 2021,
    "seedSpacing": 10,
    "randomPts": 200,
    "imageSource": 'servir',
    "assetsRoot": 'projects/ee-ltop-py/assets/',
    #the script is going to check if this folder exists and if it doesn't it will make it for you
    "assetsChild": 'LTOP_full_run', 
    "aoi": geometry,#ee.FeatureCollection("projects/servir-mekong/hydrafloods/CountryBasinsBuffer").geometry(),
    "maxClusters": 100,
    "minClusters": 10,
    # this has to be uploaded from a local directory and changed https://code.earthengine.google.com/?asset=projects/ee-ltop-py/assets/LTOP_testing/abstract_images_grid_points
    # "abstract_image_pts": ee.FeatureCollection(),
    "selectedLTparams": ee.FeatureCollection('projects/ee-ltop-py/assets/LTOP_testing/LTOP_Cambodia_troubleshooting_selected_LT_params_tc'),
    "image_source": 'comp',
    #this should be a local directory 
    "param_scoring_inputs": "/vol/v1/general_files/user_files/ben/LTOP_FTV_py_revised/output_04_lt_runs/",
    #TODO this should be explicitly constructed from args so the place name changes
    "outfile": "/vol/v1/general_files/user_files/ben/LTOP_FTV_py_revised/selected_lt_params/LTOP_Cambodia_zoomed_tc.csv",
    "njobs": 8, 

    # only needed for medoid composites
    "startDate":'11-20',
    "endDate": '03-10',
    "masked": ['cloud', 'shadow']
}