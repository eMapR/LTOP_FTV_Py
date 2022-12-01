######################################################################################################### 
##                                                                                                    #\\
##                                         LandTrendr Optimization workflow                           #\\
##                                                                                                    #\\
#########################################################################################################

# date: 2022-09-02
# author: Peter Clary        | clarype@oregonstate.edu
#         Robert Kennedy     | rkennedy@coas.oregonstate.edu
#         Ben Roberts-Pierel | robertsb@oregonstate.edu
# website: https:#github.com/eMapR/LT-GEE

import ee 
import testing_ltop as ltop 

# Initialize the library.
ee.Initialize()

def generate_kmeans_pts(*args): 
    '''
    Get a stratified random sample from the kmeans cluster image. This will yield a 
    featureCollection with one randomly assigned point per kmeans cluster id in the image. 
    '''
    args = args[0]
    kmeans_output02_2 = ltop.kmeans02_2(ee.Image(args['assetsRoot']+args['assetsChild']+"/LTOP_KMEANS_cluster_image_"+str(args['randomPts'])+"_pts_"+str(args['maxClusters'])+"_max_"+str(args['minClusters'])+"_min_clusters_"+args['place']+"_c2_"+str(args['startYear'])),
    args['aoi']
    )
    #export a fc with one point for every unique cluster id in the kmeans output

    task = ee.batch.Export.table.toAsset(
                collection=kmeans_output02_2,
                description= 'LTOP_KMEANS_stratified_points_'+str(args['maxClusters'])+'_max_'+str(args['minClusters'])+'_min_clusters_'+args['place']+'_c2_'+str(args['startYear']), 
                assetId=args['assetsRoot']+args['assetsChild']+'/LTOP_KMEANS_stratified_points_'+str(args['maxClusters'])+'_max_'+str(args['minClusters'])+'_min_clusters_'+args['place']+'_c2_'+str(args['startYear'])
) 
    task.start()
    return task.status()