######################################################################################################### 
##                                                                                                    #\\
##                      LANDTRENDR CHANGE DETECTION USING OPTIMIZATION OUTPUTS                        #\\
##                                                                                                    #\\
#########################################################################################################

# date: 2022-02-03
# author: Ben Roberts-Pierel | robertsb@oregonstate.edu
#         Peter Clary        | clarype@oregonstate.edu
#         Robert Kennedy     | rkennedy@coas.oregonstate.edu
# website: https:#github.com/eMapR/LT-GEE

# Notes on inports: 
# 1.  cluster_image - this was one of the outputs of the 02 kmeans script and an input for the 05lt_Optimum_Imager.js script 
# 2.  table - the selected LandTrendr params from the LTOP process that was also used in the 05lt_Optimum_Imager.js script. This should be from the same run as the previous arg.
# 3.  lt_vert - the image that is the output of the 05lt_Optimum_Imager.js script. This should be an array image with all the breakpoints (vertices) (up to the maxSegments specified).
# 4. export band - this is the band (or index) from the SERVIR composites that you want to manipulate and export at the end of the script. 
# 5. comps_source - this is just used for naming purposes
# 6. vertex_output - passing 'fill' or another string to the fillSegmentYear function will output segment lengths
#    passing an empty list will yield the year of the closest segment
# 7. asset_folder - this is a folder in your asssets directory where you want the outputs to end up

##################################################
##################################################
##################################################
#import modules
ltgee = require('users/emaprlab/public:Modules/LandTrendr.js') 
ftv_prep = require('users/emaprlab/broberts:LTOP_gee_revised/FTV_post_processing_modules')

#USER DEFINED INPUTS/PARAMS
startYear = 1990 
endYear = 2021 
place = 'test_geometry' 
min_obvs = 11  
startDay = '11-20' 
endDay =   '03-10'
maskThese = ['cloud','shadow', 'snow'] 
index = "NBR" 
asset_folder = 'servir_training_tests'

#change detection params 
#see https:#emapr.github.io/LT-GEE/api.html#getchangemap for info on how this works. 
changeParams = ({
delta:  'loss',
sort:   'greatest',
year:   {checked:false, start:2000, end:2020},
mag:    {checked:false, value:150,  operator:'>'},
dur:    {checked:true, value:4,    operator:'<'},
preval: {checked:false, value:300,  operator:'>'},
mmu:    {checked:false, value:1},
})


#inputs and user specified args (NOTE: change the geometry we're clipping to, currently just set up as a test)
#  aoi = ee.FeatureCollection("USDOS/LSIB/2017").filter(ee.Filter.eq('COUNTRY_NA',place)).geometry().buffer(5000)
 aoi = geometry 
#kmeans cluster image
 cluster_image = ee.Image("users/ak_glaciers/servir_training_tests/LTOP_kmeans_cluster_image_test_geometry_c2_full_area_50_per_tiled_1990") 
#selected LT params
 table = ee.FeatureCollection("users/ak_glaciers/servir_training_tests/LTOP_test_geometry_kmeans_pts_config_selected_for_GEE_upload_new_weights_gee_implementation")
#vertices image from LTOP
 lt_vert = ee.Image("users/ak_glaciers/servir_training_tests/Optimized_LT_1990_start_test_geometry_remapped_cluster_ids").clip(aoi)

##################################################
##################################################
##################################################
#prep input composites
 yr_images = [] 
  for ( y = 1990y < 2022 y++){
     im = ee.Image("projects/servir-mekong/composites/" + y.toString()) 
    yr_images.push(im) 
    
  }

   servir_ic = ee.ImageCollection.fromImages(yr_images) 
  
  #it seems like there is an issue with the dates starting on January 1. This is likely the result of a time zone difference between where 
  #the composites were generated and what the LandTrendr fit algorithm expects from the timestamps. 
  servir_ic = servir_ic.map(function(img){
     date = img.get('system:time_start') 
    return img.set('system:time_start',ee.Date(date).advance(6,'month').millis()) 
  }) 
  
  #the rest of the scripts will be easier if we just rename the bands of these composites to match what comes out of the LT modules
  #note that if using the SERVIR composites the default will be to get the first six bands without the percentile bands
   annualSRcollection = servir_ic.map(function(img){
    return img.select(['blue','green','red','nir','swir1','swir2'],['B1','B2','B3','B4','B5','B7'])
  })

#add other indices and the fitting index 
annualSRcollection = annualSRcollection.map(function(img){
 b3   = ltgee.calcIndex(img, 'B3', 0) 
 b4   = ltgee.calcIndex(img, 'B4', 0) 
 b5   = ltgee.calcIndex(img, 'B5', 1)
 b7   = ltgee.calcIndex(img, 'B7', 0)
 tcw  = ltgee.calcIndex(img, 'TCW', 1)
 tca  = ltgee.calcIndex(img, 'TCA', 1)
 ndmi = ltgee.calcIndex(img, 'NDMI', 0)
 nbr  = ltgee.calcIndex(img, 'NBR', 0)
 ndvi = ltgee.calcIndex(img, 'NDVI', 0)
return nbr.addBands(b3)
          .addBands(b4)
          .addBands(b5)
          .addBands(b7)
          .addBands(tcw)
          .addBands(tca)
          .addBands(ndmi)
          .addBands(ndvi)
          .set('system:time_start', img.get('system:time_start'))

}) 
print(annualSRcollection, 'medoid composites') 

#next the breakpoints, these are from the LTOP process
 breakpoints = ftv_prep.prepBreakpoints(lt_vert) 
####################################################
###################################################/
###################################################/
#the outputs of the LTOP workflow consist mostly of an array image of LT breakpoints. We use LT fit to generate
#fitted outputs from those breakpoints using the included composites. These things are based on the functions included in 
#the ftv_prep script which is imported at the beginning of this script. 

#run lt fit 
 lt_fit_output = ftv_prep.runLTfit(table,annualSRcollection,breakpoints,cluster_image,min_obvs) 
#it seems like the outputs of lt-fit name their bands XXX_fit while runLT does ftv_XXX_fit. I **think** these are the same thing, just w/ diff names?
#  band_names = lt_fit_output.bandNames() 
#  new_names = band_names.map(function(nm){
#   nm = ee.String(nm) 
#   return (ee.String('ftv_').cat(nm)).toLowerCase() 
# }) 

# lt_fit_output = lt_fit_output.select(band_names,new_names) 
 lt_like_output = ftv_prep.convertLTfitToLTprem(lt_fit_output,'NBR_fit',startYear,endYear) 

####################################################
###################################################/
###################################################/
#make a change detection map using the LandTrendr modules 

# add index to changeParams object
changeParams.index = 'NBR'

# get the change map layers
 changeImg = ltgee.getChangeMap(lt_like_output, changeParams)

#########################################/
# set visualization dictionaries
 palette = ['#9400D3', '#4B0082', '#0000FF', '#00FF00', '#FFFF00', '#FF7F00', '#FF0000']
 yodVizParms = {
  min: startYear,
  max: endYear,
  palette: palette
}

 magVizParms = {
  min: 1,
  max: 400,
  palette: ['#ffaa99', '#550000']
}

 durVizParms = {
  min: 1,
  max: 10,
  palette: ['#ff0000', '#999900', '#0044ee']
}

#########################################/
#Export the image outputs 
 exportIndex = index 
# Export.image.toDrive({
#   image:changeImg, 
#   description:exportIndex+'_change_detection_img_all_bands', 
#   folder:'LTOP_reem_change_detection',
#   fileNamePrefix:'NBR_change_detection_img_all_bands', 
#   region:geometry3, 
#   scale:30, 
#   crs:'EPSG:4326'
# }) 

Export.image.toAsset({
  image: changeImg, 
  description:'LT_getChangeMapper_from_LTOP_'+index, 
  assetId:asset_folder+'/LT_getChangeMapper_from_LTOP_'+index, 
  region:aoi, 
  scale:30, 
  maxPixels:1e13
}) 
Footer
© 2022 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Docs
Contact GitHub
Pricing
API
Training
Blog
About
LTOP_FTV/change_detection_from_LTOP.js at master · eMapR/LTOP_FTV