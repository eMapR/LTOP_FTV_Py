####################################################################################################### 
# \\
#                                         LandTrendr Optimization workflow                           #\\
# \\
#######################################################################################################

# date: 2023-02-20
# author: Peter Clary        | clarype@oregonstate.edu
#         Robert Kennedy     | rkennedy@coas.oregonstate.edu
#         Ben Roberts-Pierel | robertsb@oregonstate.edu
# website: https:#github.com/eMapR/LT-GEE
import ee
import ltop
import LandTrendr as ltgee
import importlib
importlib.reload(ltgee)

# Initialize the library.
ee.Initialize()


def build_image_collection(*args): 
    '''
    Construct an imageCollection on which to run kMeans. Note that the inputs to this are 
    currently HARD CODED. Note also that the function required to build medoid composites has 
    not yet been translated from js to py. 
    '''
    args = args[0] 
    if args["image_source"] == 'medoid':
        pass
        #note that this won't actually work unless we convert the buildSRcollection module in LandTrendr.js to Python
        
    elif args["image_source"] != 'medoid':
        comps = ltop.buildSERVIRcompsIC(args['startYear'],args['endYear'])
        tc = ltgee.transformSRcollection(comps, ['tcb','tcg','tcw'])
        #TODO this could probably be wrapped into a list comprehension for brevity 
        #now make a condensed time series of images 
        yearList = ee.List.sequence(1990,2021,4) 
        
        def createComposite(y):
            y = ee.Number(y)
            startDate = ee.Date.fromYMD(y,1,1)
            endDate = ee.Date.fromYMD(y.add(4),1,1)
            comp = tc.filterDate(startDate,endDate).mean()
            return comp
			
        compList = yearList.map(createComposite)
        LandsatComposites = ee.ImageCollection.fromImages(compList).toBands()
        print(LandsatComposites.bandNames().getInfo())
        
        
        org_bandLists = LandsatComposites.bandNames().getInfo()
        rename_bandLists = []
        for item in org_bandLists:
            idYear = item[:1]
            idName = item[2:]
            newName = idName + str("_")+ idYear
            rename_bandLists.append(newName)
        print(rename_bandLists)
    return LandsatComposites.select(org_bandLists,rename_bandLists)


def samplePts(pts, img, abstract=False):
    """
    Zonal statistics for points 
    """
    output = img.sampleRegions(collection= pts, scale=30, geometries = True)
    return ee.FeatureCollection(output)

# 2. cluster tusing kmeans - by generating random points
def generate_kmeans_image(*args): 
    '''
    Generates a task that is the kmeans cluster image. This is used to determine where on the landscape 
    we run different versions of LandTrendr. 
    '''
    args = args[0]
    LandsatComposites = build_image_collection(args).clip(args["aoi"])
    l8Bands = LandsatComposites.bandNames()
    
    #create some random points
    randomPts = ee.FeatureCollection.randomPoints(
        region= args["aoi"],
        points= args["randomPts"],
        seed= 23
    )
    
    #Sample over composite using random Points
    randomPts= samplePts(randomPts, LandsatComposites)
    
    # TODO this could also be done automatically. 
    kmeans_output02_1 = ltop.kmeans02_1(randomPts,LandsatComposites,
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
        maxPixels= 1e13
    )
    task.start()
    return task.status()
