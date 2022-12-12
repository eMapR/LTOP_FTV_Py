########################################################################################################
# LandTrendr Optimization (LTOP) library
########################################################################################################
#date: 2022 - 07 - 19
# author: Peter Clary | clarype @ oregonstate.edu
# Robert Kennedy | rkennedy @ coas.oregonstate.edu
# Ben Roberts - Pierel | robertsb @ oregonstate.edu
# website: https: # github.com / eMapR / LT - GEE

import ee
import lt_params as runParams
import pandas as pd 
import LandTrendr as ltgee
from google.cloud import storage
import subprocess

version = '0.1.2'
print('LTOP version: ', version)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # Build an imageCollection from SERVIR comps # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
def set_dateTime(img):
    datein = img.get('system:time_start')
    return img.set('system:time_start', ee.Date(datein).advance(6, 'month').millis())

def map_servir_ic(img):
    return img.select(['blue', 'green', 'red', 'nir', 'swir1', 'swir2'], ['B1', 'B2', 'B3', 'B4', 'B5', 'B7'])

def buildSERVIRcompsIC(startYear, endYear):
    '''
    Build an image collection from SERVIR composites. This could likely be bypassed if we just know
    what the SERVIR composites ic id is. 
    '''
    # get the SERVIR composites
    yr_images = []
    yearlist = list(range(startYear,endYear+1))
    for y in yearlist:
        im = ee.Image("projects/servir-mekong/composites/" + str(y))
        yr_images.append(im)

    servir_ic = ee.ImageCollection.fromImages(yr_images)

    # it seems like there is an issue with the dates starting on January 1. This is likely the result of a time zone difference between where
    # the composites were generated and what the LandTrendr fit algorithm expects from the timestamps.

    servir_ic = servir_ic.map(set_dateTime)

    # the rest of the scripts will be easier if we just rename the bands of these composites to match what comes out of the LT modules
    # note that if using the SERVIR composites the default will be to get the first six bands without the percentile bands
    comps = servir_ic.map(map_servir_ic)
    return comps

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 01 SNIC # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /

# run SNIC and return the imagery

def runSNIC(composites, aoi, patchSize):
    '''
    Run the GEE SNIC algorithm to 'patchify' a landscape.
    '''
    snicImagery = ee.Algorithms.Image.Segmentation.SNIC(image= composites,
                                                        size= patchSize, 
                                                        compactness= 1, ).clip(aoi)
    return snicImagery

# now split the SNIC bands

def getSNICmeanBands(snic_output):
    #TODO there is something going wrong here that is replicating bands and we're getting more than we should 
    return snic_output.select(snic_output.bandNames())#["seeds", "clusters", "B1_mean", "B2_mean", "B3_mean", "B4_mean", "B5_mean", "B7_mean", "B1_1_mean", "B2_1_mean","B3_1_mean", "B4_1_mean", "B5_1_mean", "B7_1_mean", "B1_2_mean", "B2_2_mean", "B3_2_mean", "B4_2_mean","B5_2_mean", "B7_2_mean"])

def getSNICseedBands(snic_output):
    return snic_output.select(['seeds'])

# select a singlepixel from each patch, convertto int, clip and reproject.This last step is tomimic
# the outputs of QGIS

def SNICmeansImg(snic_output, aoi):
    return getSNICseedBands(snic_output).multiply(getSNICmeanBands(snic_output))

def samplePts_helper(pt,img,abstract):
    value = img.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=pt.geometry(),
        scale=30
    )
    if not abstract: 
        return ee.Feature(pt.geometry(), value)
    else: 
        return ee.Feature(pt.geometry(), value).set('cluster_id',pt.get('cluster'))

def samplePts(pts, img, abstract=False):
    """
    Zonal statistics for points 
    """
    output = pts.map(lambda x: samplePts_helper(x,img,abstract))
    return ee.FeatureCollection(output)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 02 kMeans # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# the first handful of functions that make composites and run SNIC in the original workflow are just recycled from above.We only add the kmeans here

# train a kmeans model

def trainKmeans(snic_cluster_pts, min_clusters, max_clusters,bands):
    '''
    Train a GEE kmeans model, using the SNIC outputs as inputs. 
    '''
    training = ee.Clusterer.wekaCascadeKMeans(minClusters= min_clusters, maxClusters= max_clusters).train(
        features= snic_cluster_pts,
        #realanames= ["B1_mean", "B2_mean", "B3_mean", "B4_mean", "B5_mean", "B7_mean", "B1_1_mean", "B2_1_mean", "B3_1_mean", "B4_1_mean", "B5_1_mean", "B7_1_mean", "B1_2_mean", "B2_2_mean", "B3_2_mean", "B4_2_mean", "B5_2_mean","B7_2_mean"],
        inputProperties= bands#["B1_mean", "B2_mean", "B3_mean", "B4_mean", "B5_mean", "B7_mean", "B1_1_mean", "B2_1_mean", "B3_1_mean", "B4_1_mean", "B5_1_mean", "B7_1_mean", "B1_2_mean", "B2_2_mean", "B3_2_mean", "B4_2_mean", "B5_2_mean", "B7_2_mean"],
        #inputProperties=["seed_3", "seed_4", "seed_5", "seed_6", "seed_7", "seed_8", "seed_9", "seed_10", "seed_11", "seed_12", "seed_13", "seed_14", "seed_15", "seed_16", "seed_17","seed_18", "seed_19", "seed_20"]
    )
    return training

def runKmeans(snic_cluster_pts, min_clusters, max_clusters, aoi, snic_output,bands):
    '''
    run thekmeans model - note that the inputs are being created in the snic section in the workflow document
    '''
    # train a kmeans model
    trainedModel = trainKmeans(snic_cluster_pts, min_clusters, max_clusters,bands)
    # call the trainedkmeans model
    clusterSeed = snic_output.cluster(trainedModel) #.clip(aoi)changed 8 / 23 / 22
    return clusterSeed


def selectKmeansPts(img, aoi):
    '''
    Take a stratified random sample of the kmeans cluster image- this will yield one point for 
    every unique cluster ID in the kmeans cluster image. This is output by the kmeans algo.
    '''
    kmeans_points = img.stratifiedSample(
        numPoints= 1,
        classBand= 'cluster',
        region= aoi,
        scale= 30,
        seed= 5,
        geometries= True
    )
    return kmeans_points

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 03 abstractSampler # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /

#TODO note that this could probably be changed to the LandTrendr.py version. It was taken from there
# def computeIdnices_helper(img):
#     '''
#     Calculate Tasseled Cap Brightness, Greenness, Wetness
#     '''
#     bands = img.select(['B1', 'B2', 'B3', 'B4', 'B5', 'B7'])

#     coefficients = ee.Array([
#         [0.2043, 0.4158, 0.5524, 0.5741, 0.3124, 0.2303],
#         [-0.1603, -0.2819, -0.4934, 0.7940, -0.0002, -0.1446],
#         [0.0315, 0.2021, 0.3102, 0.1594, -0.6806, -0.6109],
#     ])

#     components = ee.Image(coefficients).matrixMultiply(bands.toArray().toArray(1)).arrayProject([0]).arrayFlatten([['TCB', 'TCG', 'TCW']]).toFloat()

#     img = img.addBands(components)

#     # Compute NDVI and NBR
#     img = img.addBands(img.normalizedDifference(['B4', 'B3']).toFloat().rename(['NDVI']).multiply(1000))
#     img = img.addBands(img.normalizedDifference(['B4', 'B7']).toFloat().rename(['NBR']).multiply(1000))

#     return img.select(['NBR', 'TCW', 'TCG', 'NDVI', 'B5']).toFloat()

def computeIndices(ic, indices = ['NBR', 'NDVI', 'TCG', 'TCW', 'B5']):
    #TODO not 100% sure this is formatted correctly 
    output_ic = ltgee.transformSRcollection(ic,indices)#ic.map(computeIdnices_helper)

    return output_ic

# Run the extraction

##############################################
#start new abstract imaging section
def generate_point_grid (cluster_ids, resolution,PRJ = "EPSG:3857"): 
  
    # Starting coordinates
    x = resolution / 2
    y = resolution / 2

    # Create a grid with some number of points and with rows of some length
    grid = []
    #TODO not sure this is the best way of doing this but we can't just iterate over the 
    #size of the fc because we need the specific cluster ids
    for i in cluster_ids.getInfo():
        # Construct the point geometry
        pt_geo = ee.Geometry.Point([x, y], PRJ)

        # Construct the output feature then join property ID
        pt = ee.Feature(pt_geo, {"cluster_id": i})

        # Increment the row position by the desired resolution
        x = x + resolution

        # Append to the grid
        grid.append(pt) 

    # Cast the grid as a feature collection
    output = ee.FeatureCollection(grid).sort('cluster_id')

    return output 

def loop_over_year(index,start_year,resolution,buffers,PRJ = "EPSG:3857"): 
    
    # Cast the input
    index = ee.Number(index)

    # Get the relevant band values from the collection of points\
    index_str = ee.Number(start_year).add(index).toInt16().format()
    original_names = [
    index_str.cat('_NBR'), index_str.cat('_TCW'), index_str.cat('_TCG'),
    index_str.cat('_NDVI'), index_str.cat('_B5')
    ]
    new_names = ['NBR','TCW','TCG','NDVI','B5']
    current_props = buffers.select(original_names, new_names)

    # Construct the synthetic image
    b1 = ee.Image([0]).toInt16().paint(current_props, "NBR").reproject(PRJ, None, resolution).rename('NBR')
    b2 = ee.Image([0]).toInt16().paint(current_props, "TCW").reproject(PRJ, None, resolution).rename('TCW')
    b3 = ee.Image([0]).toInt16().paint(current_props, "TCG").reproject(PRJ, None, resolution).rename('TCG')
    b4 = ee.Image([0]).toInt16().paint(current_props, "NDVI").reproject(PRJ, None, resolution).rename('NDVI')
    b5 = ee.Image([0]).toInt16().paint(current_props, "B5").reproject(PRJ, None, resolution).rename('B5')
    # b6 = ee.Image([0]).toInt16().paint(current_props, "B7").reproject(PRJ, None, resolution).rename('B7')
    synthetic = ee.Image.cat([b1, b2, b3, b4, b5]).rename(new_names)


    # Assign the metadata info
    metadate = ee.Date.fromYMD(ee.Number(start_year).add(index), 8, 1).millis()
    synthetic = synthetic.set('system:time_start', metadate)

    return synthetic

def buffer_func(feat,resolution,error,PRJ = "EPSG:3857"): 
    return ee.Feature(feat).buffer(resolution / 2, error, PRJ).bounds(error, PRJ)


# Unpack the join results 
def unpack_inner_join_output (feature):
    # Cast and unpack
    feature = ee.Feature(feature)
    grid_pt = ee.Feature(feature.get('primary'))
    sample_pt = ee.Feature(feature.get('secondary'))

    return grid_pt.copyProperties(sample_pt)

# Genenerate a time-series of synthetic images
def generate_synethetic_collection (point_grid, samples, start_year, end_year, resolution): 
  
    # Cast the two inputs
    point_grid = ee.FeatureCollection(point_grid)
    samples = ee.FeatureCollection(samples)

    # Join the two collections together using the cluster_id property
    join_filter = ee.Filter.equals(leftField = 'cluster_id', rightField = 'cluster_id')
    join_opperator = ee.Join.inner('primary', 'secondary')
    joined = join_opperator.apply(point_grid, samples, join_filter)

    # Unpack the join results
    grid_with_spectral = joined.map(lambda x: unpack_inner_join_output(x))
    # print(grid_with_spectral.getInfo())
    # Buffer the desired properties into squares
    error = ee.ErrorMargin(1, 'projected')
    buffers = grid_with_spectral.map(lambda x: buffer_func(x,resolution,error))
  
    # Loop over each year and construct the synthetic image
    synthetic_images = ee.ImageCollection.fromImages(
      ee.List.sequence(0, (end_year - start_year)).map(lambda x: loop_over_year(x,start_year,resolution,buffers)) #TODO convert this - the loop_over_year func needs (index,start_year,resolution,buffers): 
      )
    return synthetic_images, grid_with_spectral, samples

def mask_func(img): 
  return ee.Image(img).unmask(-9999, False)

def generate_abstract_images(sr_collection,kmeans_pts,assets_folder,grid_res,start_year,end_year,place,PRJ = "EPSG:3857"):
  '''
  Creates synthetic images in GEE by: 
  1. gets time series of imagery
  2. samples from time series using kmeans points as locations
  3. generates a synthetic image from the selected values
  4. exports the synthetic image along with points for the locations where they were sampled.
  '''
  #make sure the stratified points from kmeans are cast to a featureCollection 
  kmeans_pts = ee.FeatureCollection(kmeans_pts)

  # Specify the number of points to be extracted
  num_points = kmeans_pts.size().getInfo()

  # Unmask the values in the original collection with some unique value
  sr_collection = sr_collection.map(mask_func)

  #changed to the kmeans stratified random points 
  sample_list = samplePts(kmeans_pts,sr_collection.toBands(),abstract=True).toList(num_points)

  # Generate the grid of points 
  point_grid = generate_point_grid(kmeans_pts.aggregate_array('cluster'), grid_res)

  samples = ee.FeatureCollection(sample_list) 

  # Generate the synthetic image
  outputs = generate_synethetic_collection(point_grid, samples, start_year, end_year, grid_res)
  synthetic_collection = outputs[0]
    #   grid_points = outputs[1]
    #   sample_locations = outputs[2]

  # Export the synthetic collection to an output collection
  export_geometry = point_grid.geometry().bounds(ee.ErrorMargin(1e-3, 'projected'), PRJ)
  for cur_year in range(start_year,end_year+1): 
  # Filter the collection to get the image
      start_date = ee.Date.fromYMD(cur_year, 1, 1)
      end_date = ee.Date.fromYMD(cur_year, 12, 31)
      synthetic_image = ee.Image(synthetic_collection.filterDate(start_date, end_date).first())
#   Export the image
      task1 = ee.batch.Export.image.toAsset(
        image = synthetic_image, 
        description = "Asset-Synth-py-" + str(cur_year), 
        assetId = assets_folder + f"/{place}_synthetic_image_" + str(cur_year), 
        region = export_geometry,
        scale = grid_res, 
        crs = PRJ, 
        maxPixels = 1e13 #TODO not clear if we need to change this to 10000000000000
        )
      task1.start()
  
  # Export the original point locations
  task2 = ee.batch.Export.table.toAsset(
    collection = point_grid,
    description = "Asset-GridPoints-py", 
    assetId = assets_folder + f"/{place}_abstract_images_point_grid"
  )
  task2.start()
  return None

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 04 abstractImager # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# note that the versions of LT were moved out of this space to a separate script (lt_params.py)

# function to create a timestamp for the abstract images
# Add a time stamp based on the system:id property

def addTimeStamp(image):
    # Get the year from the system:id property
    year = ee.Number.parse(ee.String(image.get('system:id')).slice(-4)).toInt16()

    # Create a date object
    date = ee.Date.fromYMD(year, 8, 1).millis()

    return image.set('system:time_start', date)

# Update the mask to remove the no - data values so they don 't mess
# up running LandTrendr - - assumes the no - data value is -32768

def maskNoDataValues(img):
    # Create the mask
    img_mask = img.neq(-32768)
    return img.updateMask(img_mask)

def getPoint2(geom, img, z):
    return img.reduceRegions(collection=geom, 
                            reducer = 'first', 
                            scale = z) #.getInfo()

def runLTversionsHelper2(feature,selectedParams, indexName):
    return feature.set('index', indexName).set('params',selectedParams).set('param_num', selectedParams['param_num']) 

def convertArr(arr_img,bands,mask): 
    #sometimes the source and fitted are different sizes, this will mess things up with array masking so do it as a multiband image then go back to array
    img = arr_img.arrayProject([0]).arrayFlatten([bands])
    #mask then convert back to an array image
    return img.updateMask(mask).toArray()

def fillZeroRMSE(rmse_img,source_img,fit_img,startYear,endYear): 
    '''
    Take the RMSE band of LT output from GEE and recalculate any instances where RMSE == 0. 
    The RMSE would jsut be to difference all of the years source minus fitted, square the entire vector, add it up and then take the square root.
    and it would have to be for each index.
    '''
    rmse_img = ee.Image(rmse_img)
    # mask = rmse_img.eq(0)
    # bands = [f'yr_{n}' for n in range(startYear,endYear+1)]
    # source_img = convertArr(source_img,bands,mask)
    # fit_img = convertArr(fit_img,bands,mask)
 
    #now calculate new RMSE
    diff = source_img.subtract(fit_img).pow(2)
    arr_sum = diff.arrayReduce(ee.Reducer.sum(),[1])
    rmse = arr_sum.divide(diff.arrayLength(1)).sqrt().arrayProject([0]).arrayFlatten([['rmse']]) #TODO double check that this is right
    # rmse = arr_sum.sqrt()
    #this is still an array image so we have to convert back to img
    # rmse_img = rmse.arrayProject([0]).arrayFlatten([['rmse']])
    #now go back and update the 0 value locations in the RMSE image
    return ee.Image(rmse_img.updateMask(rmse_img.neq(0)).unmask(ee.Image(rmse)))

def runLTversionsHelper(param,indexName,id_points,startYear,endYear):
    # this statment finds the index of the parameter being used
    # index = fullParams.index(param)

    # here we select the index image on which to run LandTrendr
    # fullParams[index]["timeseries"] = ic.select([indexName])
    #cast a row of the pandas df to dict so the LT call knows what to do with it 

    # run LandTrendr
    lt = ee.Algorithms.TemporalSegmentation.LandTrendr(timeSeries=param['timeseries'],
                                                       maxSegments=param['maxSegments'],
                                                       spikeThreshold=param['spikeThreshold'],
                                                       vertexCountOvershoot = param['vertexCountOvershoot'],
                                                       preventOneYearRecovery = param['preventOneYearRecovery'],
                                                       recoveryThreshold = param['recoveryThreshold'],
                                                       pvalThreshold = param['pvalThreshold'],
                                                       bestModelProportion = param['bestModelProportion'],
                                                       minObservationsNeeded = param['minObservationsNeeded']
                                                        )#param)#(fullParams[index])

    # select the segmenation data from LandTrendr

    ltlt = lt.select(['LandTrendr'])
    # slice the LandTrendr data into sub arrays

    yearArray = ltlt.arraySlice(0, 0, 1).rename(['year'])

    sourceArray = ltlt.arraySlice(0, 1, 2).rename(['orig'])

    fittedArray = ltlt.arraySlice(0, 2, 3).rename(['fitted'])

    vertexMask = ltlt.arraySlice(0, 3, 4).rename(['vert'])

    #fill in rmse values of zero that result from the GEE implementation of LT
    rmse = fillZeroRMSE(lt.select(['rmse']),sourceArray,fittedArray,startYear,endYear)#.toArray()
    # rmse = rmse.select(['rmse'])

    # place each array into a image stack one array per band
    lt_images = yearArray.addBands(sourceArray).addBands(fittedArray).addBands(vertexMask).addBands(rmse)

    # #add an aoi for testing
    # aoi = ee.Geometry.Polygon(
    #     [[[104.35274437489917, 13.834579257069725],
    #       [104.35274437489917, 13.747888760904075],
    #       [104.62053612294605, 13.747888760904075],
    #       [104.62053612294605, 13.834579257069725]]])

    # task = ee.batch.Export.image.toAsset(
    #         image= lt_images,#ee.FeatureCollection(multipleLToutputs).flatten(),#combinedLToutputs,
    #         description= indexName+'_testing_lt_images',
    #         assetId='projects/ee-ltop-py/assets/ltop_image_testing/'+indexName+'_testing_lt_images',
    #         region = aoi,
    #         scale=30
            
    #     )

    # task.start()
    # extract a LandTrendr pixel time series at a point
    getpin2 = getPoint2(id_points, lt_images,20)  #scale changed from 20 to 30 BRP add scale 30 some points(cluster_id 1800 for example) do not extract lt data.I compared the before change output with the after the chagne output and the data that was in both datasets matched.compared 1700 to 1700...

    # maps over a feature collection that holds the LandTrendr data and adds attributes: index, params and param number.

    attriIndexToData = getpin2.map(lambda x: runLTversionsHelper2(x,param,indexName)) 

    return attriIndexToData

def flip_index(ic,indexName): 
    '''
    Apply the LandTrendr indexFlipper function. TODO there is probably already some code to do this. 
    '''
    #this will return an item from a dictionary that looks like {'INDEX':flip} with flip being 1 or -1. 
    flip = ltgee.indexFlipper(indexName)
    print('The index thing looks like: ')
    print(flip)

    return ic.map(lambda i: ee.Image(i).multiply(ee.Number(flip)).set('system:time_start',i.get('system:time_start')))

def runLTversions(ic, indexName, id_points,startYear,endYear,imageSource):
    # here we map over each LandTrendr parameter ation, appslying eachation to the abstract image
    #TODO its not entirely clear what's going on here but a list can't be mapped over apparently so it was changed to a list comprehension
    #first try converting the list to a fc
    # LTParams = ee.List(runParams.runParams).map(lambda x: ee.Feature(None,x))
    # LTParams = ee.FeatureCollection(LTParams)
    param_list = runParams.generate_lt_param_combos()
    df = pd.DataFrame.from_dict(param_list)#changed 12/1/22 BRP for on the fly generation ,index=range(len(runParams.runParams)))
    
    #I think this was inserting an ic in each line of code but in this format we should be able 
    # to just fill the whole thing in one go because its going to run a bunch of differnt
    # LT configs with a different fitting index and then go onto the next fitting index 
        # fullParams[index]["timeseries"] = ic.select([indexName])
    # df['timeseries'] = None
    #insert a little code here to flip the indices that need to be flipped
    #TODO decide if this is where this should go or if it would be better to put it up in the abstract images
    if imageSource.lower() == 'servir': 
        corrected_ic = flip_index(ee.ImageCollection(ic.select([indexName])),indexName)
        df['timeseries'] = corrected_ic#ee.ImageCollection(ic.select([indexName]))#corrected_ic
    else: 
        df['timeseries'] = ee.ImageCollection(ic.select([indexName]))
    #this was previously an index, replicate it as it was
    # df['param_num'] = range(df.shape[0])
    dictParams = df.to_dict(orient='records')
    # print(dictParams)
    printer = [runLTversionsHelper(x,indexName,id_points,startYear,endYear) for x in dictParams]
    # printer = [runLTversionsHelper(x,ic,indexName,id_points) for x in runParams.runParams]
    # printer = runParams.map(runLTversionsHelper)
    # printer = df.apply(runLTversionsHelper,args=(ic,indexName,id_points))
    # printer = LTParams.map(lambda x: runLTversionsHelper(x,LTParams,ic,indexName,id_points)) 

    return printer

def mergeLToutputs(lt_outputs):
    # empty table? to a merged feature collection featCol

    # loop over each feature collection and merges them into one
    for i in range(len(lt_outputs)):
        if i == 0:
            featCol = lt_outputs[0]
        elif i > 0 :
            featCol = featCol.merge(lt_outputs[i])

    return featCol

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 05 Optimized Imager # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
def printer_helper_two(img,cluster_mask):
    '''
    Masks img (one of every image in ic) using clusters drawn from kmeans output image.
    '''
    return img.updateMask(cluster_mask).set('system:time_start', img.get('system:time_start'))
    

def printer_helper(feat,ic,cluster_image,aoi):
    # changes feature object to dictionary
    dic = ee.Feature(feat).toDictionary()

    # calls number value from dictionary feature key, maxSegments.
    maxSeg = dic.getNumber('maxSegments')

    # calls number value from dictionary feature key, spikeThreshold.
    spikeThr = dic.getNumber('spikeThreshold')

    # calls number value from dictionary feature  key, "recoveryThreshold".
    recov = dic.getNumber("recoveryThreshold")

    # calls number value from dictionary feature key, "pvalThreshold"
    pval = dic.getNumber("pvalThreshold")

    #define the timeSeries param so it can be filled below - TODO not totally clear if this is necessary
    timeSeries = ee.ImageCollection([])

    # get cluster ID from dictionary feature as a number

    cluster_id = ee.Number(dic.get('cluster_id')).float()

    # creates a mask keep pixels for only a single cluster - changed for something more simple cluster_mask = cluster_image.eq(cluster_id).selfMask()

    # blank maskcol
    cluster_mask = cluster_image.eq(cluster_id).selfMask()
    # maps over image collection applying the mask to each image
    maskcol = ic.map(lambda x: printer_helper_two(x,cluster_mask))


    # apply masked image collection to LandTrendr parameter dictionary
    # runParamstemp["timeseries"] = maskcol
    timeSeries = maskcol
    # Runs LandTrendr

    lt = ee.Algorithms.TemporalSegmentation.LandTrendr(timeSeries = timeSeries,
                                                        maxSegments = maxSeg,
                                                        spikeThreshold = spikeThr,
                                                        vertexCountOvershoot = 3,
                                                        preventOneYearRecovery = True,
                                                        recoveryThreshold = recov,
                                                        pvalThreshold = pval,
                                                        bestModelProportion = 0.75,
                                                        minObservationsNeeded = maxSeg
                                                        ).clip(aoi)  # .select(0) #.unmask()

    # return LandTrendr image collection run to list.
    return lt

# Run the versions of LT we selected, uses masks to run the correct version for the SNIC patches in a given kmeans cluster
# input args are the index tables above and the associated imageCollection
def printerFunc(fc, ic, cluster_image, aoi):

    output = fc.map(lambda x: printer_helper(x,ic,cluster_image,aoi))
    # this might be a little redundant but its a way to deal with the map statements
    return output

def filterTable(pt_list, index):
    return pt_list.filter(ee.Filter.eq('index', index))

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # GCS functions # # # # # # # # # # # # # # # # # # # # # # # # 
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#helper functions to upload and download to Google Cloud bucket 
def download_from_bucket(bucket_name,download_file,destination_fn,credentials='creds.json'): 
    """
    Download data from a bucket. 
    """
    storage_client = storage.Client.from_service_account_json(
        credentials)
    # Initialise a client
    # storage_client = storage.Client(project_name)
    # bucket = storage_client.get_bucket(bucket_name)

    # Create a bucket object for our bucket
    bucket = storage_client.get_bucket(bucket_name)
    # Create a blob object from the filepath - like "folder_one/foldertwo/filename.extension"
    blob = bucket.blob(download_file)
    # Download the file to a destination
    blob.download_to_filename(destination_fn)
    return None 

def download_multiple_from_bucket(bucket_name,file_list,out_fns,credentials='creds.json'): 
    """
    Download data from a bucket. 
    """
    storage_client = storage.Client.from_service_account_json(
        credentials)
    # Initialise a client
    # storage_client = storage.Client(project_name)
    # bucket = storage_client.get_bucket(bucket_name)

    # Create a bucket object for our bucket
    bucket = storage_client.get_bucket(bucket_name)
    # Create a blob object from the filepath - like "folder_one/foldertwo/filename.extension"
    for n in range(len(file_list)): 
        #make sure the input files are being writtent to the right output file 
        blob = bucket.blob(sorted(file_list)[n])
        # Download the file to a destination
        blob.download_to_filename(sorted(out_fns)[n])
    return True

#example call
#download_from_bucket('ltop_assets_storage','LTOP_cambodia_test_selected_params','/vol/v1/general_files/user_files/ben/LTOP_FTV_py_revised/output_test.csv','ltop-gdrive-downloads')


#pip install --upgrade google-cloud-storage. 
def upload_to_bucket(blob_name, path_to_file, bucket_name,credentials='creds.json'):
    """ Upload data to a bucket"""
     
    # Explicitly use service account credentials by specifying the private key
    # file.
    storage_client = storage.Client.from_service_account_json(
        credentials)

    #print(buckets = list(storage_client.list_buckets())

    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path_to_file)
    
    #returns a public url
    return blob.public_url

#example call
#upload_to_bucket('LTOP_cambodia_test_selected_params','/vol/v1/general_files/user_files/ben/LTOP_FTV_py_revised/selected_lt_params/LTOP_Cambodia_zoomed_tc.csv','ltop_assets_storage')

def check_single_gcs_file(gcs_file,bucket_name,credentials='creds.json'):   
    storage_client = storage.Client.from_service_account_json(
        credentials)
    # storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    stats = storage.Blob(bucket=bucket, name=gcs_file).exists(storage_client)
    return stats

def check_multiple_gcs_files(file_list,bucket_name,credentials='creds.json'):   
    storage_client = storage.Client.from_service_account_json(
        credentials)
    # storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    for file in file_list: 
        stats = storage.Blob(bucket=bucket, name=file).exists(storage_client)
        if stats: 
            continue
        else: 
            return False

    return stats

def create_gee_asset_from_gcs(asset_id,gcloud_uri,gee_assets_dir): 
    # request_id = ee.data.newTaskId()[0]
    asset_id = gee_assets_dir+'/'+asset_id
    print('asset id is: ',asset_id)
    print('and glcoud uri is: ',gcloud_uri)
    #this commandline version works: earthengine upload table --asset_id=projects/ee-ltop-py/assets/LTOP_full_run/LTOP_cambodia_tc gs:#ltop_assets_storage/LTOP_Cambodia_tc.csv
    # gee_params = {
    #     'name':asset_id,
    #     'uris':gcloud_uri,
    #     # maybe need some other stuff here
    # }
    subprocess.run(f'earthengine upload table --asset_id={asset_id} {gcloud_uri}',shell=True)
    # ee.data.startIngestion(request_id=request_id, params=gee_params)
    return None 

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # Stabilization functions # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /

#the outputs of LTOP have to be converted to an array and empty (0) entries have to be removed 
def prepBreakpoints(ltop_output): 
    arr = ltop_output.toArray() 
    mask = ltop_output.gt(0).toArray()
    #apply the mask to the array   
    return arr.arrayMask(mask)  

#example run
# prepBreakpoints = prepBreakpoints_helper(ltop_output)
    
###################################################/

#prepare the breakpoints for use in the LandTrendr fit algorithm
#get the bp years between two end point years. In the case that there is no bp in the start year we need to set that as a breakpoint 
#so the time series is bookended when we do the fit 
def clipBreakpoints(startYear,LTOP_band,lt_vert): 
    '''
    #this function is only required if the input imageCollection is shorter than the thing you used to create breakpoints
    #LTOP_band is a band that doesn't exist in the inputs but is structured in the same way
    #lt_vert is the output of the LTOP process and should be an array image of LT breakpoints 
  
    '''
    #create an image of constant value with starting year val. This will be used to ensure we have the starting bp
    yearImg = ee.Image.constant(startYear).select(['constant'],[LTOP_band]) 

    #get the array of breakpoints from the LTOP outputs 
    bps = lt_vert.toArray() 
  
    #create a mask that gets rid of everything before the start year plus one. We add one to make sure that when we add the start 
    #year back in we don't get the start year twice (duplicate breakpoints)
    mask = lt_vert.gte(startYear+1).toArray() 
  
    #apply the mask to the array 
    bps = bps.arrayMask(mask) 
    #add the constant image above as an array with the start year as the constant value
    bps = bps.arrayCat(
    image2=yearImg.toArray(),
    axis=0
    ) 
    #sort the array values so that the breakpoint years are in chronological order after adding a band
    bps = bps.arraySort() 
    return bps  


# Insert a process that selects different spikeThreshold params for LT based on the different K-means clusters from the optimization process. This is a masking process
#whereby each of the options for spikeThreshold are selected and used as a mask to run different paramaterizations of LT-fit and then those are patched backtogether at the end.
def runLTfit_helper(spike,table,kmeans_image):
     #the output of this function is a list of masks, each mask has the value of the spikeThreshold for the clusters that should be 
    #run with that value in those places
    #first we have to get any pixels that have a cluster id with the spikeThreshold value we're looking for 
    clusters = table.filter(ee.Filter.eq('spikeThreshold',spike)) 
    #then we get a list of all the cluster_ids with that spike threshold value
    clusters = clusters.aggregate_array('cluster_id') 
    #next we get all the pixels from the cluster image that match the cluster ids selected in the previous step (create a mask)
    mask = kmeans_image.remap(clusters,ee.List.repeat(1,clusters.length())) 
    #add a prop with the spikeThreshold value so we can query it later
    return mask.set('spikeThreshold',spike) 

def runLTfit_mask_helper(msk,ic,breakpoints,min_obvs): 
    #map over the ic, masking each image in the collection as we go
    ic = ic.map(lambda img: img.updateMask(msk))
    #run LandTrendr
    lt_servir = ee.Algorithms.TemporalSegmentation.LandTrendrFit(
        timeSeries=ic,
        vertices=breakpoints,
        spikeThreshold=msk.get('spikeThreshold'),
        minObservationsNeeded=min_obvs
      )
    return lt_servir 

def runLTfit(table,input_ic,breakpoints,kmeans_image,min_obvs): 
    #first get all the possible spikeThreshold values 
    spike_vals = table.aggregate_array('spikeThreshold').distinct() 

    #go through the distinct spikeThreshold vals, filter or mask the image 
    #to get each value and use that as a mask to get the areas of the constant image that we want 
    
    
    filter_pixels = spike_vals.map(lambda x: runLTfit_helper(x,table,kmeans_image))
  
    #these are the masks we want for running LandTrendr fit 
    spike_masks = ee.ImageCollection.fromImages(filter_pixels) 
  
    #run LandTrendr
    masked_ic = spike_masks.map(lambda msk: runLTfit_mask_helper(msk,input_ic,breakpoints,min_obvs))
    
  
    #combine the masked versions of LT into an image
    combined = masked_ic.mosaic() 
    return combined 

###################################################/
def backwardsDifference(array): 
    right = array.arraySlice(0, 0, -1) 
    left = array.arraySlice(0, 1) 
    return left.subtract(right) 

def forwardDifference(array): 
    left = array.arraySlice(0, 0, -1) 
    right = array.arraySlice(0, 1) 
    return left.subtract(right) 

def convertLTfitToLTprem(lt_fit_output,export_band,startYear,endYear): 
    '''
    Convert the outputs of LT fit to look like the outputs of LT premium (i.e., 4xn array). 
    '''
    #select one band to test the outputs of the LT fit step. This has each year as a band. 
    ftv = lt_fit_output.select([export_band]) 
  
    #make a list of years then images to fill the first row of the array
    years = ee.List.sequence(startYear,endYear,1)
    #define a function that makes a list of constant images 
    yrs_img = years.map(lambda x: ee.Image.constant(x)) 
    #create an array image of years
    yrs_img = ee.ImageCollection.fromImages(yrs_img).toBands().toArray() 
  
    #now create the source values- we don't have these so fill with a noData value 
    source_vals = ee.Image.constant(-9999).toArray()
    source_vals = source_vals.arrayRepeat(0,years.length()) 
  
    #next we create the isVertex row of the table. This has a one if the year is a breakpoint and 0 if not
    #there's probably a cleaner way to do this part 
   
    #these are the delta outputs but they can only have a duration of one year
    deltas = backwardsDifference(ftv) 
  
    #make shifted delta outputs. Taking these differences should give the location of the breakpoints? 
    yod = forwardDifference(deltas) #year of detection
    ones = ee.Image(ee.Array([1])) 
    #prepend a one - when we take deltas of deltas to get the years it changed everything to shift by a year. 
    #we also lose the first and last breakpoint years because no changes occurred in those years. We need to those to 
    #calculate the magnitude of change for each segment so we need to add ones for those so that they are selected from the 
    #raw data when segment magnitude changes are calculated. 
    yod = (ones.addBands(yod).toArray(0)).toInt() #cast to int because there's a weird floating pt thing going on 
    #add a 1 at the end- because this was based on the deltas we lost the last item in the array but we want it for the mask
    yod = yod.addBands(ones).toArray(0) 
    #now make a mask
    isVertex = yod.neq(0)
  
    #now put all the pieces together 
    #first concat the first two rows together 
    arr1 = yrs_img.arrayCat(source_vals,1) 
    #then combine the second two rows 
    arr2 = ftv.toArray().arrayCat(isVertex,1)
    #then combine the 2 2D arrays- it seems like arrayCat won't let you combine a 2d array with a 1d array 
    #also rename the default array band to match the outputs of premium Landtrendr for the disturbance mapping 
    lt_out = arr1.arrayCat(arr2,1).arrayTranspose() 
    lt_out = lt_out.addBands(ee.Image.constant(1)).select(['array','constant'],['LandTrendr','rmse']) 

    return lt_out 

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # Invoking functions # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# now set up functions for calling each step.These are like wrappers for the above functions and are called externally.
# it may make more sense to just put the things from the five scripts into this section so we can ditch those 

# # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # 01 SNIC # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # #
def snic01(snic_composites, aoi, random_pts, patch_size):
    # run the SNIC algorithm
    SNICoutput = runSNIC(snic_composites, aoi, patch_size)

    SNICpixels = SNICmeansImg(SNICoutput, aoi)

    # these were previously the two things that were exported to drive

    SNICimagery = SNICoutput.toInt32() #.reproject({crs: 'EPSG:4326', scale: 30}) # previously snicImagery

    SNICmeans = SNICpixels.toInt32().clip(aoi) # previously SNIC_means_image

    #create some random points
    snicPts = ee.FeatureCollection.randomPoints(
        region= aoi,
        points= random_pts,
        seed= 10
    )
    # do the sampling
    snicPts = samplePts(snicPts, SNICimagery)

    return ee.List([snicPts, SNICimagery])


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 02 kMeans # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
def kmeans02_1(snicPts, SNICimagery, aoi, min_clusters, max_clusters):
    # take the snic outputs from the previous steps and thentrain and run a kmeans model
    snic_bands = SNICimagery.bandNames()
    snic_bands = snic_bands.remove('clusters')
    snic_bands = snic_bands.remove('seeds')
    snicKmeansImagery = ee.Image(SNICimagery).select(snic_bands)#["B1_mean", "B2_mean", "B3_mean", "B4_mean", "B5_mean", "B7_mean", "B1_1_mean", "B2_1_mean", "B3_1_mean","B4_1_mean", "B5_1_mean", "B7_1_mean", "B1_2_mean", "B2_2_mean", "B3_2_mean", "B4_2_mean", "B5_2_mean","B7_2_mean"])

    kMeansImagery = runKmeans(snicPts, min_clusters, max_clusters, aoi, snicKmeansImagery,snic_bands)

    # kMeansPoints = selectKmeansPts(kMeansImagery, aoi)
    return kMeansImagery
    # return ee.List([kMeansImagery, kMeansPoints])


def kmeans02_2(kmeans_imagery, aoi):

    kMeansPoints = selectKmeansPts(kmeans_imagery, aoi)

    return kMeansPoints

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 03 abstractSampler # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
def rename_kmeans(feat):
    return feat.set('cluster_id', feat.get('cluster'))

def abstractSampler03_1(full_timeseries, kMeansPts, assets_folder, grid_res, startYear, endYear,place):

    # rename the kmeans points dataset cluster col to cluster_id, that 's what the remaining scripts expect
    kMeansPts = kMeansPts.map(rename_kmeans)

    # add spectral indices to the annual ic
    images_w_indices = computeIndices(full_timeseries)
    #TODO add an indexFlipper so make sure that TCW and TCG gets flipped

    #this is set up to just trigger the creation of the abstract images 
    abstractImageOutputs = generate_abstract_images(images_w_indices,kMeansPts,assets_folder,grid_res,startYear,endYear,place)

    return abstractImageOutputs

def abstractSampler03_2(img_path, startYear, endYear):

    # this has to be called separately after the first half is dealt with outside GEE
    # replaces the manual creation of an imageCollection after uploading abstract images

    abstractImages = []
    yearlist = list(range(startYear,endYear+1))
    for y in yearlist:
        img = ee.Image(img_path+str(y))
        abstractImages.append(img)

    # this is the primary input to the 04 script
    abstractImagesIC = ee.ImageCollection.fromImages(abstractImages)
    return abstractImagesIC

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # 04abstractImager # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
def abstractImager04(abstractImagesIC, place, id_points, gcs_bucket, startYear,endYear,testing,imageSource): 
    # wrap this into a for loop
    indices = ['NBR', 'NDVI', 'TCG', 'TCW', 'B5']

    # Add a time stamp to each image
    abstractImagesIC = abstractImagesIC.map(addTimeStamp)

    # Mask the "no-data" values
    abstractImagesIC = abstractImagesIC.map(maskNoDataValues)

    # Rename the bands(can 't upload with names as far as I can tell)
    # abstractImagesIC = abstractImagesIC.select(['b1', 'b2', 'b3', 'b4', 'b5'], indices) # changed to uppercase
 
    for i in range(len(indices)):
        # this calls the printer function that runs different versions of landTrendr
        multipleLToutputs = runLTversions(abstractImagesIC, indices[i], id_points,startYear,endYear,imageSource)
        
        # this merges the multiple LT runs
        combinedLToutputs = mergeLToutputs(multipleLToutputs)

        # then export the outputs - the paramater selection can maybe be done in GEE at some point but its
        # a big python script that needs to be translated into GEE
        if testing.lower() == 'true':  
            task = ee.batch.Export.table.toDrive(
                collection= combinedLToutputs,#ee.FeatureCollection(multipleLToutputs).flatten(),#combinedLToutputs,
                selectors = ['cluster_id','fitted','index','orig','param_num','params','rmse','vert','year','.geo'],
                description= "LTOP_" + place + "_abstractImageSample_lt_144params_" + indices[i] + "_c2_selected",
                folder= "LTOP_TESTING_" + place + "_abstractImageSamples_c2",
                fileFormat= 'CSV'
            )
        else: 
            task = ee.batch.Export.table.toCloudStorage(
                collection = combinedLToutputs,
                description = "LTOP_" + place + "_abstractImageSample_lt_144params_" + indices[i] + "_c2_selected",
                bucket = gcs_bucket,
                selectors = ['cluster_id','fitted','index','orig','param_num','params','rmse','vert','year','.geo'],
                fileFormat = 'CSV'
            )

        task.start()
    return None

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 05 Optimized Imager # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# cast the feature collection(look up table) to list so we can filter and map it.
def optimizedImager05(table, annualSRcollection, kmeans_output, aoi):
    lookUpList = table.toList(table.size())

    # transformed Landsat surface reflectance image collection 
    annualLTcollectionNBR = ltgee.buildLTcollection(annualSRcollection, 'NBR', ["NBR"]).select(["NBR", "ftv_nbr"],["NBR", "ftv_ltop"])
    annualLTcollectionNDVI = ltgee.buildLTcollection(annualSRcollection, 'NDVI', ["NDVI"]).select(["NDVI", "ftv_ndvi"],["NDVI", "ftv_ltop"])
    annualLTcollectionTCW = ltgee.buildLTcollection(annualSRcollection, 'TCW', ["TCW"]).select(["TCW", "ftv_tcw"],["TCW", "ftv_ltop"])
    annualLTcollectionTCG = ltgee.buildLTcollection(annualSRcollection, 'TCG', ["TCG"]).select(["TCG", "ftv_tcg"], ["TCG", "ftv_ltop"])
    annualLTcollectionB5 = ltgee.buildLTcollection(annualSRcollection, 'B5', ["B5"]).select(["B5", "ftv_b5"],["B5", "ftv_ltop"])
    # now call the function for each index we're interested in
    printerB5 = printerFunc(filterTable(lookUpList, 'B5'), annualLTcollectionB5, kmeans_output, aoi)
    printerNBR = printerFunc(filterTable(lookUpList, 'NBR'), annualLTcollectionNBR, kmeans_output, aoi)
    printerNDVI = printerFunc(filterTable(lookUpList, 'NDVI'), annualLTcollectionNDVI, kmeans_output, aoi)
    printerTCG = printerFunc(filterTable(lookUpList, 'TCG'), annualLTcollectionTCG, kmeans_output, aoi)
    printerTCW = printerFunc(filterTable(lookUpList, 'TCW'), annualLTcollectionTCW, kmeans_output, aoi)

    # concat each index print output together
    combined_lt = printerB5.cat(printerNBR).cat(printerNDVI).cat(printerTCG).cat(printerTCW)

    # Mosaic each LandTrendr run in list to single image collection
    ltcol = ee.ImageCollection(combined_lt).mosaic()

    params = {
        "timeseries": ltcol,
        "maxSegments": 10,
        "spikeThreshold": 5,
        "vertexCountOvershoot": 3,
        "preventOneYearRecovery": True,
        "recoveryThreshold": 5,
        "pvalThreshold": 5,
        "bestModelProportion": 0.75,
        "minObservationsNeeded": 5
        }
    # create the vertices in the form of an array image
    lt_vert = ltgee.getLTvertStack(ltcol, params).select([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).int16()
    return lt_vert