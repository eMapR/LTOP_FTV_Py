########################################################################################################
# LandTrendr Optimization (LTOP) library
########################################################################################################
#date: 2022 - 07 - 19
# author: Peter Clary | clarype @ oregonstate.edu
# Robert Kennedy | rkennedy @ coas.oregonstate.edu
# Ben Roberts - Pierel | robertsb @ oregonstate.edu
# website: https: # github.com / eMapR / LT - GEE

import ee
import params
import lt_params as runParams
import pandas as pd 
import LandTrendr as ltgee
# from LandTrendr import getLTvertStack, buildLTcollection
# This library holds modules for running an optimized version of the LandTrendr algorithm.The process addresses an
# issue of paramaterizing the LT algorithm for different types of land cover / land use.

#ltgee = require('users/ak_glaciers/adpc_servir_LTOP:modules/LandTrendr.js')
#params = require('users/ak_glaciers/adpc_servir_LTOP:modules/params.js')

version = params.params["version"]
#exports.version = version
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # Build an imageCollection from SERVIR comps # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
def set_dateTime(img):
    datein = img.get('system:time_start')
    return img.set('system:time_start', ee.Date(datein).advance(6, 'month').millis())

def map_servir_ic(img):
    return img.select(['blue', 'green', 'red', 'nir', 'swir1', 'swir2'], ['B1', 'B2', 'B3', 'B4', 'B5', 'B7'])

def buildSERVIRcompsIC(startYear, endYear):

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

#exports.buildSERVIRcompsIC = buildSERVIRcompsIC
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 01 SNIC # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /

# run SNIC and return the imagery

def runSNIC(composites, aoi, patchSize):
    snicImagery = ee.Algorithms.Image.Segmentation.SNIC(image= composites,size= patchSize, compactness= 1, ).clip(aoi)
    return snicImagery

#exports.runSNIC = runSNIC

# now split the SNIC bands

def getSNICmeanBands(snic_output):
    return snic_output.select(snic_output.bandNames())#["seeds", "clusters", "B1_mean", "B2_mean", "B3_mean", "B4_mean", "B5_mean", "B7_mean", "B1_1_mean", "B2_1_mean","B3_1_mean", "B4_1_mean", "B5_1_mean", "B7_1_mean", "B1_2_mean", "B2_2_mean", "B3_2_mean", "B4_2_mean","B5_2_mean", "B7_2_mean"])

def getSNICseedBands(snic_output):
    return snic_output.select(['seeds'])

# select a singlepixel from each patch, convertto int, clip and reproject.This last step is tomimic
# the outputs of QGIS

def SNICmeansImg(snic_output, aoi):
    return getSNICseedBands(snic_output).multiply(getSNICmeanBands(snic_output))

#exports.SNICmeansImg = SNICmeansImg

# now we mimic the part that was happening in QGIS where we make noData, convert pixels to pts, subset and get seed data


def pixelsToPts(img, aoi):
    # convert
    vectors = img.sample(
            region= aoi, #.geometry().buffer(-250),
            geometries= True,
            scale= 30,
            projection= 'EPSG:4326',
    )
    return ee.FeatureCollection(vectors)


# subset fc

def subsetFC(fc, grid_pts_max):
    output_fc = fc.randomColumn(
        columnName= 'random',
        seed= 2,
        distribution= 'uniform'
    )
    output_fc = ee.FeatureCollection(output_fc.sort('random').toList(grid_pts_max).slice(0, grid_pts_max))
    return output_fc


# #exports.subsetFC = subsetFC

# def splitPixIm_helper(feat):
#     tile_bounds = feat.geometry().buffer(-250)  # could be changed

#     img_tile = means_img.clip(tile_bounds)  # remove this if it errors

#     pts = pixelsToPts(means_img, tile_bounds)
#     # try subsetting the points here before putting them back together to reduce the size of the dataset
#     pts = subsetFC(pts, pts_per_tile)
#     return pts

# # there is an issue where GEE complains if we straight convert pixels to points because there are too many.Try tiling the image and converting those first.
# def splitPixImg(means_img, grid, pts_per_tile):

#     # we map over the grid tiles, subsetting the image
#     tile_pts = grid.map(splitPixIm_helper)

#     return tile_pts.flatten()


#exports.splitPixImg = splitPixImg

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
# thefirst handful of functions that make composites and run SNIC in the original workflow are just recycled from above.We only add the kmeans here
# note also that the band structure is different in this version than what 's generated in QGIS

# train a means model

def trainKmeans(snic_cluster_pts, min_clusters, max_clusters,bands):


    training = ee.Clusterer.wekaCascadeKMeans(minClusters= min_clusters, maxClusters= max_clusters).train(
        features= snic_cluster_pts,
        #realanames= ["B1_mean", "B2_mean", "B3_mean", "B4_mean", "B5_mean", "B7_mean", "B1_1_mean", "B2_1_mean", "B3_1_mean", "B4_1_mean", "B5_1_mean", "B7_1_mean", "B1_2_mean", "B2_2_mean", "B3_2_mean", "B4_2_mean", "B5_2_mean","B7_2_mean"],
        inputProperties= bands#["B1_mean", "B2_mean", "B3_mean", "B4_mean", "B5_mean", "B7_mean", "B1_1_mean", "B2_1_mean", "B3_1_mean", "B4_1_mean", "B5_1_mean", "B7_1_mean", "B1_2_mean", "B2_2_mean", "B3_2_mean", "B4_2_mean", "B5_2_mean", "B7_2_mean"],
        #inputProperties=["seed_3", "seed_4", "seed_5", "seed_6", "seed_7", "seed_8", "seed_9", "seed_10", "seed_11", "seed_12", "seed_13", "seed_14", "seed_15", "seed_16", "seed_17","seed_18", "seed_19", "seed_20"]
    )
    return training


# run thekmeans model - note that the inputs are being created in the snic section in the workflow document
def runKmeans(snic_cluster_pts, min_clusters, max_clusters, aoi, snic_output,bands):
    # train a kmeans model
    trainedModel = trainKmeans(snic_cluster_pts, min_clusters, max_clusters,bands)
    # call the trainedkmeans model
    clusterSeed = snic_output.cluster(trainedModel) #.clip(aoi)changed 8 / 23 / 22
    return clusterSeed


#exports.runKmeans = runKmeans


def selectKmeansPts(img, aoi):

    kmeans_points = img.stratifiedSample(
        numPoints= 1,
        classBand= 'cluster',
        region= aoi,
        scale= 30,
        seed= 5,
        geometries= True
    )
    return kmeans_points


#exports.selectKmeansPts = selectKmeansPts

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 03 abstractSampler # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /

# make function to calculate spectral indices
def computeIdnices_helper(img):
    # Calculate Tasseled Cap Brightness, Greenness, Wetness

    bands = img.select(['B1', 'B2', 'B3', 'B4', 'B5', 'B7'])

    coefficients = ee.Array([
        [0.2043, 0.4158, 0.5524, 0.5741, 0.3124, 0.2303],
        [-0.1603, -0.2819, -0.4934, 0.7940, -0.0002, -0.1446],
        [0.0315, 0.2021, 0.3102, 0.1594, -0.6806, -0.6109],
    ])

    components = ee.Image(coefficients).matrixMultiply(bands.toArray().toArray(1)).arrayProject([0]).arrayFlatten([['TCB', 'TCG', 'TCW']]).toFloat()

    img = img.addBands(components)

    # Compute NDVI and NBR
    img = img.addBands(img.normalizedDifference(['B4', 'B3']).toFloat().rename(['NDVI']).multiply(1000))
    img = img.addBands(img.normalizedDifference(['B4', 'B7']).toFloat().rename(['NBR']).multiply(1000))

    return img.select(['NBR', 'TCW', 'TCG', 'NDVI', 'B5']).toFloat()

def computeIndices(ic):

    output_ic = ic.map(computeIdnices_helper)

    return output_ic


#exports.computeIndices = computeIndices

# Run the extraction

##############################################
#start new abstract imaging section
##################################################/
################ Import modules ##########################/
##################################################/
import ee 
import params
import ltop 

# print(ee.__version__)

# Trigger the authentication flow.
# ee.Authenticate()

# Initialize the library.
ee.Initialize()

# GLOBAL IABLES
PRJ = "EPSG:3857"

'''
This script demonstrates how to generate a synthetic image in 
GEE alone without using the Python API or local downloads.

The demonstration consists of the following steps:
1. Generating an medoid time-series over a small area
2. Sampling the values from the medoid time series
3. Generating a synthetic image from the sampled values
4. Exporting the synthetic image as an asset along with the relevant point collections (original and grid)
'''


# Add a sequential ID to a set of points
# def add_sequential_id (cur, prev): 
  
#     # Cast the inputs
#     cur = ee.Feature(cur)
#     prev = ee.List(prev)

#     # Get the ID value from the previous feature
#     prev_id = ee.Feature(prev.get(-1)).getNumber("GRID_ID")

#     # Assign the new grid ID
#     cur = cur.set("cluster_id", prev_id.add(1).toInt64())

#     return prev.add(cur)
  
  
# Generate a grid of points. Resolution and row length can be specified. 

def generate_point_grid (cluster_ids, resolution): 
  
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

        # Construct the output feature the join property ID
        pt = ee.Feature(pt_geo, {"cluster_id": i})

        # Increment the row position by the desired resolution
        x = x + resolution

        # Append to the grid
        grid.append(pt) #this was previously concat, that should be a js convention which we can change to append? 

    # Cast the grid as a feature collection
    output = ee.FeatureCollection(grid).sort('cluster_id')

    return output 

def loop_over_year(index,start_year,resolution,buffers): 
    
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
    #  b7 = ee.Image([0]).toInt16().paint(current_props, "B7").reproject(PRJ, null, resolution).rename('B7')
    synthetic = ee.Image.cat([b1, b2, b3, b4, b5]).rename(new_names)


    # Assign the metadata info
    metadate = ee.Date.fromYMD(ee.Number(start_year).add(index), 8, 1).millis()
    synthetic = synthetic.set('system:time_start', metadate)

    return synthetic

def buffer_func(feat,resolution,error): 
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

    # Join the two collections togeheter using the cluster_id property
    join_filter = ee.Filter.equals(leftField = 'cluster_id', rightField = 'cluster_id')
    join_opperator = ee.Join.inner('primary', 'secondary')
    joined = join_opperator.apply(point_grid, samples, join_filter)

    # Unpack the join results
    grid_with_spectral = joined.map(lambda x: unpack_inner_join_output(x))

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

def generate_abstract_images(sr_collection,kmeans_pts,assets_folder,grid_res,start_year,end_year):

  #make sure the stratified points from kmeans are cast to a featureCollection 
  kmeans_pts = ee.FeatureCollection(kmeans_pts)

  # Specify the number of points to be extracted
  num_points = kmeans_pts.size().getInfo()

  ##/ Code ##

  # TODO Generate a time-series from servir composites - this could also be passed as an arg? 
#   sr_collection = ltop.buildSERVIRcompsIC(start_year,end_year) 

  # Unmask the values int the original collection with some unique value
  sr_collection = sr_collection.map(mask_func)

  #changed to the kmeans stratified random points 
  sample_list = samplePts(kmeans_pts,sr_collection.toBands(),abstract=True).toList(num_points)

  # Generate the grid of points 
  point_grid = generate_point_grid(kmeans_pts.aggregate_array('cluster'), grid_res)

  samples = ee.FeatureCollection(sample_list) #note that this is hard coded 

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
        assetId = assets_folder + "/synthetic_image_" + str(cur_year), 
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
    assetId = assets_folder + "/abstract_images_point_grid"
  )
  task2.start()
  return None






#DEPRECATED?
# def runExtraction(images, points, start_year, end_year):

#     # Function that is applied to each year function
#     def inner_map(year):
#         # Cast the input
#         year = ee.Number(year).toInt16()

#         # Construct the dates to filter the image collection
#         start_date = ee.Date.fromYMD(year, 1, 1)
#         end_date = ee.Date.fromYMD(year, 12, 31)

#         # Get the image to sample
#         current_image = ee.Image(images.filterDate(start_date, end_date).first()).addBands(ee.Image.constant(year).rename('year')).unmask(-32768).toInt16()

#         # Run an extraction
#         extraction = current_image.reduceRegions(
#             collection= points,
#             reducer= ee.Reducer.first(),
#             scale= 30,
#         )

#         return extraction.toList(points.size())# Peter



#     # Create a list of years to map over
#     years = ee.List.sequence(start_year, end_year)

#     # Flatten the outputs
#     outputs = ee.FeatureCollection(ee.List(years.map(inner_map)).flatten())

#     return outputs


#exports.runExtraction = runExtraction

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 04 abstractImager # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# define some LT paramsfor the different versions of LT run below:
#LandTrendr Parameters
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
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

#OLD VERSION?
# def getPoint2(geom, img, z):
#     return img.reduceRegions(collection=geom, 
#                             reducer = 'first', 
#                             scale = z) #.getInfo()

# def runLTversionsHelper2(feature,fullParams,indexName,index):
#     return feature.set('index', indexName).set('params', fullParams[index]).set('param_num', index)

# def runLTversionsHelper(param,fullParams,ic,indexName,id_points):
#     # this statment finds the index of the parameter being used
#     index = fullParams.index(param)

#     # here we select the index image on which to run LandTrendr
#     fullParams[index]["timeseries"] = ic.select([indexName])

#     # run LandTrendr

#     lt = ee.Algorithms.TemporalSegmentation.LandTrendr(fullParams[index])

#     # select the segmenation data from LandTrendr

#     ltlt = lt.select(['LandTrendr'])

#     # slice the LandTrendr data into sub arrays

#     yearArray = ltlt.arraySlice(0, 0, 1).rename(['year'])

#     sourceArray = ltlt.arraySlice(0, 1, 2).rename(['orig'])

#     fittedArray = ltlt.arraySlice(0, 2, 3).rename(['fitted'])

#     vertexMask = ltlt.arraySlice(0, 3, 4).rename(['vert'])

#     rmse = lt.select(['rmse'])

#     # place each array into a image stack one array per band
#     lt_images = yearArray.addBands(sourceArray).addBands(fittedArray).addBands(vertexMask).addBands(rmse)

#     # extract a LandTrendr pixel time series at a point
#     getpin2 = getPoint2(id_points, lt_images,20)  # add scale 30 some points(cluster_id 1800 for example) do not extract lt data.I compared the before change output with the after the chagne output and the data that was in both datasets matched.compared 1700 to 1700...

#     # maps over a feature collection that holds the LandTrendr data and adds attributes: index, params and param number.

#     attriIndexToData = getpin2.map(lambda x: runLTversionsHelper2(x,fullParams,indexName,index)) 

#     return attriIndexToData

def getPoint2(geom, img, z):
    return img.reduceRegions(collection=geom, 
                            reducer = 'first', 
                            scale = z) #.getInfo()

def runLTversionsHelper2(feature,selectedParams, indexName):
    return feature.set('index', indexName).set('params',selectedParams).set('param_num', selectedParams['param_num']) #TODO note the zero is just a filler!!!

def runLTversionsHelper(param,indexName,id_points):
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

    rmse = lt.select(['rmse'])

    # place each array into a image stack one array per band
    lt_images = yearArray.addBands(sourceArray).addBands(fittedArray).addBands(vertexMask).addBands(rmse)

    # extract a LandTrendr pixel time series at a point
    getpin2 = getPoint2(id_points, lt_images,20)  # add scale 30 some points(cluster_id 1800 for example) do not extract lt data.I compared the before change output with the after the chagne output and the data that was in both datasets matched.compared 1700 to 1700...

    # maps over a feature collection that holds the LandTrendr data and adds attributes: index, params and param number.

    attriIndexToData = getpin2.map(lambda x: runLTversionsHelper2(x,param,indexName)) 

    return attriIndexToData

def runLTversions(ic, indexName, id_points):
    # here we map over each LandTrendr parameter ation, appslying eachation to the abstract image
    #TODO its not entirely clear what's going on here but a list can't be mapped over apparently so it was changed to a list comprehension
    #first try converting the list to a fc
    # LTParams = ee.List(runParams.runParams).map(lambda x: ee.Feature(None,x))
    # LTParams = ee.FeatureCollection(LTParams)
    
    df = pd.DataFrame.from_records(runParams.runParams)#,index=range(len(runParams.runParams)))

    #I think this was inserting an ic in each line of code but in this format we should be able 
    # to just fill the whole thing in one go because its going to run a bunch of differnt
    # LT configs with a different fitting index and then go onto the next fitting index 
        # fullParams[index]["timeseries"] = ic.select([indexName])
    df['timeseries'] = None
    df["timeseries"] = ee.ImageCollection(ic.select([indexName]))
    #this was previously an index, not sure if its actually needed but just replicate it as it was
    df['param_num'] = range(df.shape[0])
    dictParams = df.to_dict(orient='records')
    printer = [runLTversionsHelper(x,indexName,id_points) for x in dictParams]
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


#exports.mergeLToutputs = mergeLToutputs

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

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # Invoking functions # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# now set up functions for calling each step.These are like wrappers for the above functions and are called externally.

# # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # 01 SNIC # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # #
def snic01(snic_composites, aoi, random_pts, patch_size):
    # run the SNIC algorithm
    SNICoutput = runSNIC(snic_composites, aoi, patch_size)

    SNICpixels = SNICmeansImg(SNICoutput, aoi)

    # these were previouslythe two things that were exported to drive

    SNICimagery = SNICoutput.toInt32() #.reproject({crs: 'EPSG:4326', scale: 30}) # previously snicImagery

    SNICmeans = SNICpixels.toInt32().clip(aoi) # previously SNIC_means_image

    # try just creating some random points
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


#exports.kmeans02_1 = kmeans02_1
#exports.kmeans02_2 = kmeans02_2
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 03 abstractSampler # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
def rename_kmeans(feat):
    return feat.set('cluster_id', feat.get('cluster'))

def abstractSampler03_1(full_timeseries, kMeansPts, assets_folder, grid_res, startYear, endYear):

    # rename the kmeans points dataset cluster col to cluster_id, that 's what the remaining scripts expect
    kMeansPts = kMeansPts.map(rename_kmeans)

    # add spectral indices to the annual ic
    images_w_indices = computeIndices(full_timeseries)

    #this is set up to just trigger the creation of the abstract images 
    abstractImageOutputs = generate_abstract_images(images_w_indices,kMeansPts,assets_folder,grid_res,startYear,endYear)


    ##################
    #DEPRECATED?
    # # extract values from the composites at the points created in the kmeans step above

    # spectralExtraction = runExtraction(images_w_indices, kMeansPts, startYear, endYear)
    #####################
    # Select out the relevant bands
    # abstractImageOutputs = spectralExtraction.select(['cluster_id', 'year', 'NBR', 'TCW', 'TCG', 'NDVI', 'B5'], None,False) #.sort('cluster_id') null and false are the old js arguments


    return abstractImageOutputs


#exports.abstractSampler03_1 = abstractSampler03_1

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

#exports.abstractSampler03_2 = abstractSampler03_2

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # 04abstractImager # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
def abstractImager04(abstractImagesIC, place, id_points): 
    # wrap this into a for loop
    indices = ['NBR', 'NDVI', 'TCG', 'TCW', 'B5']

    # Add a time stamp to each image
    abstractImagesIC = abstractImagesIC.map(addTimeStamp)

    # Mask the "no-data" values
    abstractImagesIC = abstractImagesIC.map(maskNoDataValues)

    # Rename the bands(can 't upload with names as far as I can tell)
    # abstractImagesIC = abstractImagesIC.select(['b1', 'b2', 'b3', 'b4', 'b5'], indices) # changed to uppercase
 
    for i in range(len(indices)):
        # print(indices[i])
        # this calls the printer function that runs different versions of landTrendr
        multipleLToutputs = runLTversions(abstractImagesIC, indices[i], id_points)
        
        #DEPRECATED??
        # this merges the multiple LT runs
        combinedLToutputs = mergeLToutputs(multipleLToutputs)

        # then export the outputs - the paramater selection can maybe be done in GEE at some point but its
        # a big python script that needs to be translated into GEE
        task = ee.batch.Export.table.toDrive(
            collection= combinedLToutputs,#ee.FeatureCollection(multipleLToutputs).flatten(),#combinedLToutputs,
            selectors = ['cluster_id','fitted','index','orig','param_num','params','rmse','vert','year','.geo'],
            description= "LTOP_" + place + "_abstractImageSample_lt_144params_" + indices[i] + "_c2_selected",
            folder= "LTOP_" + place + "_abstractImageSamples_c2",
            fileFormat= 'CSV'
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


#exports.optimizedImager05 = optimizedImager05
