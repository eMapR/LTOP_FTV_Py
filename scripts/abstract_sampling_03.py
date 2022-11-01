######################################################################################################### 
##                                                                                                    #\\
##                               Step 3 LandTrendr Optimization workflow                              #\\
##                                                                                                    #\\
#########################################################################################################

# date: 2022-09-02
# author: Peter Clary        | clarype@oregonstate.edu
#         Robert Kennedy     | rkennedy@coas.oregonstate.edu
#         Ben Roberts-Pierel | robertsb@oregonstate.edu
# website: https:#github.com/eMapR/LT-GEE

##################################################/
################ Import modules ##########################/
##################################################/

import ee
import params
import ltop

# Initialize the library.
ee.Initialize()


#this is what the new function to create these looks like:     output = generate_abstract_images(kmeans_pts,aoi,assets_folder,grid_res,start_year,end_year):
#note also that they're going to generate automatically from inside the function(s)
def create_abstract_imgs(*args): 
  args = args[0]

  #these composites are used for the last two steps and span the full period
  if args["image_source"] == 'medoid': 
      pass
      # annualSRcollection = ltgee.buildSRcollection(startYear, endYear, startDate, endDate, aoi, masked); 

  elif args["image_source"] != 'medoid':
      annualSRcollection = ltop.buildSERVIRcompsIC(args['startYear'],args['endYear']); 
      annualSRcollection = annualSRcollection.filterBounds(args['aoi'])
  
  abstract_output03_1 = ltop.abstractSampler03_1(annualSRcollection,
                                                  ee.FeatureCollection(args['assetsRoot']+args['assetsChild']+'/LTOP_KMEANS_stratified_points_'+str(args['maxClusters'])+'_max_'+str(args['minClusters'])+'_min_clusters_'+args['place']+'_c2_'+str(args['startYear'])),#str(args['startYear'])),
                                                  args['assetsRoot']+args['assetsChild'],
                                                  30, #TODO add to params? 
                                                  args['startYear'], 
                                                  args['endYear'],
                                                  args['place']
                                                  ) 

  return None 
#DEPRECATED?
# Export the points 
# task = ee.batch.Export.table.toDrive(
#   collection = abstract_output03_1, 
#   description = "LTOP_"+params.place+"_Abstract_Sample_annualSRcollection_NBRTCWTCGNDVIB5_c2_"+params.startYear.toString()+"_start_tc", 
#   fileNamePrefix = "LTOP_"+params.place+"_Abstract_Sample_annualSRcollection_NBRTCWTCGNDVIB5_c2_"+params.startYear.toString()+"_start_tc", 
#   folder = params.place+'_abstract_images',
#   fileFormat = 'csv'
# )

 