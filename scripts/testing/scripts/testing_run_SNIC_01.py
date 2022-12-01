######################################################################################################### 
##                                                                                                    #\\
##                              Step 1 LandTrendr Optimization workflow                               #\\
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
# import params
import testing_LandTrendr as ltgee
import importlib
importlib.reload(ltgee)
import testing_ltop as ltop
# print(ee.__version__)

# Trigger the authentication flow.
# ee.Authenticate()

# Initialize the library.
ee.Initialize()
        
def build_image_collection(*args): 
    '''
    Construct an imageCollection on which to run SNIC. Note that the inputs to this are 
    currently HARD CODED. Note also that the function required to build medoid composites has 
    not yet been translated from js to py. 
    '''
    args = args[0] 
    if args["image_source"] == 'medoid':
        pass
        #note that this won't actually work unless we convert the buildSRcollection module in LandTrendr.js to Python
        # imageEnd = ltgee.buildSRcollection(2021, 2021, params["startDate"], params["endDate"], params["aoi"], params["masked"]).mosaic()
        # imageMid = ltgee.buildSRcollection(2005, 2005, params["startDate"], params["endDate"], params["aoi"], params["masked"]).mosaic()
        # imageStart = ltgee.buildSRcollection(1990, 1990, params["startDate"], params["endDate"], params["aoi"], params["masked"]).mosaic()

        # LandsatComposites = imageEnd.addBands(imageMid).addBands(imageStart)
    elif args["image_source"] != 'medoid':
        comps = ltop.buildSERVIRcompsIC(args['startYear'],args['endYear'])
        tc = ltgee.transformSRcollection(comps, ['tcb','tcg','tcw'])
        #TODO this could probably be wrapped into a list comprehension for brevity 
        #now make an image out of a start, mid and end point of the time series 
        image21 = tc.filter(ee.Filter.eq('system:index','2021')).first()
        image18 = tc.filter(ee.Filter.eq('system:index','2018')).first()
        image14 = tc.filter(ee.Filter.eq('system:index','2014')).first()
        image10 = tc.filter(ee.Filter.eq('system:index','2010')).first()
        image06 = tc.filter(ee.Filter.eq('system:index','2006')).first()
        image02 = tc.filter(ee.Filter.eq('system:index','2002')).first()
        image98 = tc.filter(ee.Filter.eq('system:index','1998')).first()
        image94 = tc.filter(ee.Filter.eq('system:index','1994')).first()
        image90 = tc.filter(ee.Filter.eq('system:index','1990')).first()
        LandsatComposites = image90.addBands(image94).addBands(image98).addBands(image02).addBands(image06).addBands(image10).addBands(image14).addBands(image18).addBands(image21)
    return LandsatComposites

# 1. run the snic algorithm 
def generate_snic_outputs(*args):
    '''
    Generate two tasks: 
    1. The SNIC imagary that groups pixels into spectrally similar patches. 
    2. A featureCollection of patch centroids that will be used for the kMeans algorithm. 
    '''
    args = args[0] 
    LandsatComposites = build_image_collection(args)

    snic_output01 = ltop.snic01(LandsatComposites,args["aoi"],args["randomPts"],args["seedSpacing"])

    task = ee.batch.Export.table.toAsset(
                collection= snic_output01.get(0),
                description="LTOP_SNIC_pts_"+args["place"]+"_c2_"+str(args["randomPts"])+"_pts_"+str(args["startYear"]),
                assetId= args["assetsRoot"]+args["assetsChild"]+"/LTOP_SNIC_pts_"+args["place"]+"_c2_"+str(args["randomPts"])+"_pts_"+str(args["startYear"]),
                
    )

    task2 = ee.batch.Export.image.toAsset(
                image= ee.Image(snic_output01.get(1)),
                description="LTOP_SNIC_imagery_"+args["place"]+"_c2_"+str(args["randomPts"])+"_pts_"+str(args["startYear"]),
                assetId=args["assetsRoot"]+args["assetsChild"]+"/LTOP_SNIC_imagery_"+args["place"]+"_c2_"+str(args["randomPts"])+"_pts_"+str(args["startYear"]),
                region= args["aoi"],
                scale=30,
                maxPixels=10000000000000
    )

    task.start()
    task2.start()

    return task.status(), task2.status()
            



