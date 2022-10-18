####################################################################################################### 
# \\
#                                         LandTrendr Optimization workflow                           #\\
# \\
#######################################################################################################

# date: 2022-09-02
# author: Peter Clary        | clarype@oregonstate.edu
#         Robert Kennedy     | rkennedy@coas.oregonstate.edu
#         Ben Roberts-Pierel | robertsb@oregonstate.edu
# website: https:#github.com/eMapR/LT-GEE
import ee
import ltop

# Initialize the library.
ee.Initialize()

# 2. cluster the snic patches with kmeans - added a filter to remove points that didn't get valid values in previous step
def generate_kmeans_image(*args): 
    '''
    Generates a task that is the kmeans cluster image. This is used to determine where on the landscape 
    we run different versions of LandTrendr. 
    '''
    args = args[0]
    #note that paths need to be changed to access a Google cloud project 
    kmeans_output02_1 = ltop.kmeans02_1(ee.FeatureCollection(
        args["assetsRoot"] + args["assetsChild"] + "/LTOP_SNIC_pts_" + args["place"] + "_c2_" + str(args["randomPts"]) + "_pts_" + str(args["startYear"])).filter(ee.Filter.neq('B1_mean', None)),
        ee.Image(args["assetsRoot"] + args["assetsChild"] + "/LTOP_SNIC_imagery_" + args["place"] + "_c2_" + str(args["randomPts"]) + "_pts_" + str(args["startYear"])),
        args["aoi"],
        args["minClusters"],
        args["maxClusters"]
        )

    # export the kmeans output image to an asset
    task = ee.batch.Export.image.toAsset(
        image= kmeans_output02_1,  # kmeans_output02.get(0),
        description= "LTOP_KMEANS_cluster_image_" + str(args["randomPts"]) + "_pts_" + str(args["maxClusters"]) + "_max_" + str(args["minClusters"]) + "_min_clusters_" + args["place"] + "_c2_" + str(args["startYear"]),
        assetId= args["assetsRoot"] +args["assetsChild"] + "/LTOP_KMEANS_cluster_image_" + str(args["randomPts"]) + "_pts_" + str(args["maxClusters"]) + "_max_" + str(args["minClusters"]) + "_min_clusters_" + args["place"] + "_c2_" + str(args["startYear"]),
        region= args["aoi"],
        scale= 30,
        maxPixels= 10000000000000
    )
    task.start()
    return task.status()