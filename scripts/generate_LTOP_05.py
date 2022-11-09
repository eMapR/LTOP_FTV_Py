######################################################################################################### 
##                                                                                                    #\\
##                                Step 5 LandTrendr Optimization workflow                             #\\
##                                                                                                    #\\
#########################################################################################################

# date: 2022-09-02
# author: Peter Clary        | clarype@oregonstate.edu
#         Robert Kennedy     | rkennedy@coas.oregonstate.edu
#         Ben Roberts-Pierel | robertsb@oregonstate.edu
# website: https:#github.com/eMapR/LT-GEE

import ee
import ltop

# Initialize the library.
ee.Initialize()

def generate_LTOP_breakpoints(*args):
   args = args[0]
   #naming convention based on previously generated image
   cluster_img = ee.Image(args['assetsRoot']+args['assetsChild']+"/LTOP_KMEANS_cluster_image_"+str(args['randomPts'])+"_pts_"+str(args['maxClusters'])+"_max_"+str(args['minClusters'])+"_min_clusters_"+args['place']+"_c2_"+str(args['startYear']))
   #these composites are used for the last two steps and span the full period
   if args["image_source"] == 'medoid':
      pass
      # annualSRcollection = ltgee.buildSRcollection(params.startYear, params.endYear, params.startDate, params.endDate, params.aoi, params.masked); 

   elif args["image_source"] != 'medoid':
      annualSRcollection = ltop.buildSERVIRcompsIC(args['startYear'],args['endYear']); 

   # 5. create the optimized output
   optimized_output05 = ltop.optimizedImager05(args['selectedLTparams'],annualSRcollection,cluster_img,args['aoi']) #note that table is the selected paramaters from the python script after step four

   task = ee.batch.Export.image.toAsset(
      image = optimized_output05,
      description = 'Optimized_LT_'+str(args['startYear'])+'_start_'+args['place']+'_all_cluster_ids_tc',
      assetId = args['assetsRoot']+args['assetsChild']+'/Optimized_LT_'+str(args['startYear'])+'_start_'+args['place']+'_all_cluster_ids_tc',
      region = args['aoi'],
      scale = 30,
      maxPixels = 1e13
   )   

   task.start()

   return task.status()