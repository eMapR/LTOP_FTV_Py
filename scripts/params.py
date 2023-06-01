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
#TODO things will get confused if you do not create a new folder and you've changed some params, do something about that
place = 'Cambodia_full'
assetsRoot = 'projects/ee-ltop-py/assets/'
assetsChild = 'LTOP_py_Cambodia'

params = {
    "place": place,
    "startYear": 1990,
    "endYear": 2021,
    "seedSpacing": 10,
    "randomPts": 20000,
    "imageSource": 'servir',
    "assetsRoot": assetsRoot,
    #the script is going to check if this folder exists and if it doesn't it will make it for you
    "assetsChild": assetsChild, 
    #note that whatever you use here needs to be cast as a geometry before running
    "aoi":ee.FeatureCollection("USDOS/LSIB/2017").filter(ee.Filter.eq('COUNTRY_NA','Cambodia')).geometry(),
    # "aoi": geometry,#ee.FeatureCollection("projects/servir-mekong/hydrafloods/CountryBasinsBuffer").geometry(),
    "maxClusters": 2500,
    "minClusters": 2500,
    # this has to be uploaded from a local directory and changed https://code.earthengine.google.com/?asset=projects/ee-ltop-py/assets/LTOP_testing/abstract_images_grid_points
    # "abstract_image_pts": ee.FeatureCollection(),
    "selectedLTparams": ee.FeatureCollection(assetsRoot+assetsChild+'/'+'LTOP_'+place+'_selected_LT_params_tc'),
    "image_source": 'comp',
    #these should be local directories
    #this one will be created automatically if it does not exist 
    "param_scoring_inputs": f"/vol/v1/general_files/user_files/ben/LTOP_FTV_py_revised/output_04_{place}/",
    "outfile": f"/vol/v1/general_files/user_files/ben/LTOP_FTV_py_revised/selected_lt_params/LTOP_{place}_selected_LT_params_tc.csv",
    "njobs": 8, 
    #note that this must be set up in advance, the script will not do it for you!!
    "cloud_bucket":"ltop_assets_storage",

    # only needed for medoid composites
    "startDate":'11-20',
    "endDate": '03-10',
    "masked": ['cloud', 'shadow']
}