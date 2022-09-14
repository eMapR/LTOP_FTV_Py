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

#exports.buildSERVIRcompsIC = buildSERVIRcompsIC;
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 01 SNIC # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /

# run SNIC and return the imagery

def runSNIC(composites, aoi, patchSize):
    snicImagery = ee.Algorithms.Image.Segmentation.SNIC(image= composites,size= patchSize, compactness= 1, ).clip(aoi)
    return snicImagery

#exports.runSNIC = runSNIC;

# now split the SNIC bands

def getSNICmeanBands(snic_output):
    return snic_output.select(["seeds", "clusters", "B1_mean", "B2_mean", "B3_mean", "B4_mean", "B5_mean", "B7_mean", "B1_1_mean", "B2_1_mean","B3_1_mean", "B4_1_mean", "B5_1_mean", "B7_1_mean", "B1_2_mean", "B2_2_mean", "B3_2_mean", "B4_2_mean","B5_2_mean", "B7_2_mean"])

def getSNICseedBands(snic_output):
    return snic_output.select(['seeds'])

# select a singlepixel from each patch, convertto int, clip and reproject.This last step is tomimic
# the outputs of QGIS

def SNICmeansImg(snic_output, aoi):
    return getSNICseedBands(snic_output).multiply(getSNICmeanBands(snic_output))

#exports.SNICmeansImg = SNICmeansImg;

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
    output_fc = ee.FeatureCollection(output_fc.sort('random').toList(grid_pts_max).slice(0, grid_pts_max));
    return output_fc;


# #exports.subsetFC = subsetFC;

def splitPixIm_helper(feat):
    tile_bounds = feat.geometry().buffer(-250);  # could be changed

    img_tile = means_img.clip(tile_bounds);  # remove this if it errors

    pts = pixelsToPts(means_img, tile_bounds);
    # try subsetting the points here before putting them back together to reduce the size of the dataset
    pts = subsetFC(pts, pts_per_tile);
    return pts;

# there is an issue where GEE complains if we straight convert pixels to points because there are too many.Try tiling the image and converting those first.
def splitPixImg(means_img, grid, pts_per_tile):

    # we map over the grid tiles, subsetting the image
    tile_pts = grid.map(splitPixIm_helper)

    return tile_pts.flatten();


#exports.splitPixImg = splitPixImg;



def samplePts(pts, img):
    imgg = img
    def samplePts_helper(pt):
        value = imgg.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=pt.geometry(),
            scale=30
        )
        return ee.Feature(pt.geometry(), value)

    output = pts.map(samplePts_helper)

    return ee.FeatureCollection(output);


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 02 kMeans # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# thefirst handful of functions that make composites and run SNIC in the original workflow are just recycled from above.We only add the kmeans here
# note also that the band structure is different in this version than what 's generated in QGIS

# train a means model

def trainKmeans(snic_cluster_pts, min_clusters, max_clusters):


    training = ee.Clusterer.wekaCascadeKMeans(minClusters= min_clusters, maxClusters= max_clusters).train(
        features= snic_cluster_pts,
        #realanames= ["B1_mean", "B2_mean", "B3_mean", "B4_mean", "B5_mean", "B7_mean", "B1_1_mean", "B2_1_mean", "B3_1_mean", "B4_1_mean", "B5_1_mean", "B7_1_mean", "B1_2_mean", "B2_2_mean", "B3_2_mean", "B4_2_mean", "B5_2_mean","B7_2_mean"],
        inputProperties= ["B1_mean", "B2_mean", "B3_mean", "B4_mean", "B5_mean", "B7_mean", "B1_1_mean", "B2_1_mean", "B3_1_mean", "B4_1_mean", "B5_1_mean", "B7_1_mean", "B1_2_mean", "B2_2_mean", "B3_2_mean", "B4_2_mean", "B5_2_mean", "B7_2_mean"],
        #inputProperties=["seed_3", "seed_4", "seed_5", "seed_6", "seed_7", "seed_8", "seed_9", "seed_10", "seed_11", "seed_12", "seed_13", "seed_14", "seed_15", "seed_16", "seed_17","seed_18", "seed_19", "seed_20"]
    )
    return training;


# run thekmeans model - note that the inputs are being created in the snic section in the workflow document
def runKmeans(snic_cluster_pts, min_clusters, max_clusters, aoi, snic_output):
    # train a kmeans model
    trainedModel = trainKmeans(snic_cluster_pts, min_clusters, max_clusters)
    # call the trainedkmeans model
    clusterSeed = snic_output.cluster(trainedModel) #.clip(aoi);changed 8 / 23 / 22
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
    return kmeans_points;


#exports.selectKmeansPts = selectKmeansPts;

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 03 abstractSampler # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /

# make function to calculate spectral indices
def computeIdnices_helper(img):
    # Calculate Tasseled Cap Brightness, Greenness, Wetness

    bands = img.select(['B1', 'B2', 'B3', 'B4', 'B5', 'B7']);

    coefficients = ee.Array([
        [0.2043, 0.4158, 0.5524, 0.5741, 0.3124, 0.2303],
        [-0.1603, -0.2819, -0.4934, 0.7940, -0.0002, -0.1446],
        [0.0315, 0.2021, 0.3102, 0.1594, -0.6806, -0.6109],
    ]);

    components = ee.Image(coefficients).matrixMultiply(bands.toArray().toArray(1)).arrayProject([0]).arrayFlatten([['TCB', 'TCG', 'TCW']]).toFloat();

    img = img.addBands(components);

    # Compute NDVI and NBR
    img = img.addBands(img.normalizedDifference(['B4', 'B3']).toFloat().rename(['NDVI']).multiply(1000));
    img = img.addBands(img.normalizedDifference(['B4', 'B7']).toFloat().rename(['NBR']).multiply(1000));

    return img.select(['NBR', 'TCW', 'TCG', 'NDVI', 'B5']).toFloat();

def computeIndices(ic):

    output_ic = ic.map(computeIdnices_helper)

    return output_ic;


#exports.computeIndices = computeIndices;

# Run the extraction


def runExtraction(images, points, start_year, end_year):

    # Function that is applied to each year function
    def inner_map(year):
        # Cast the input
        year = ee.Number(year).toInt16();

        # Construct the dates to filter the image collection
        start_date = ee.Date.fromYMD(year, 1, 1);
        end_date = ee.Date.fromYMD(year, 12, 31);

        # Get the image to sample
        current_image = ee.Image(images.filterDate(start_date, end_date).first()).addBands(ee.Image.constant(year).rename('year')).unmask(-32768).toInt16()

        # Run an extraction
        extraction = current_image.reduceRegions(
            collection= points,
            reducer= ee.Reducer.first(),
            scale= 30,
        )

        return extraction.toList(points.size())# Peter



    # Create a list of years to map over
    years = ee.List.sequence(start_year, end_year)

    # Flatten the outputs
    outputs = ee.FeatureCollection(ee.List(years.map(inner_map)).flatten())

    return outputs


#exports.runExtraction = runExtraction

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 04 abstractImager # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# define some LT paramsfor the different versions of LT run below:
#LandTrendr Parameters
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# ideally, this is moved into another more user friendly / readable format

runParams = [{"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3, "preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThrec": 0.05, "bestModelProportion": 0.75,"minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75,"minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 6, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 6},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 8, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 8},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 10, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 10},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.75, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 0.9, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.25, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.5, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 0.9, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.05, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.1, "bestModelProportion": 0.75, "minObservationsNeeded": 11},
             {"timeseries": ee.ImageCollection([]), "maxSegments": 11, "spikeThreshold": 1.0, "vertexCountOvershoot": 3,"preventOneYearRecovery": True, "recoveryThreshold": 1.0, "pvalThreshold": 0.15, "bestModelProportion": 0.75, "minObservationsNeeded": 11}]

# function to create a timestamp for the abstract images
# Add a time stamp based on the system:id property

def addTimeStamp(image):
    # Get the year from the system:id property
    year = ee.Number.parse(ee.String(image.get('system:id')).slice(-4)).toInt16();

    # Create a date object
    date = ee.Date.fromYMD(year, 8, 1).millis();

    return image.set('system:time_start', date);


# Update the mask to remove the no - data values so they don 't mess
# up running LandTrendr - - assumes the no - data value is -32768

def maskNoDataValues(img):
    # Create the mask
    img_mask = img.neq(-32768)
    return img.updateMask(img_mask)



def getPoint2(geom, img, z):
    return img.reduceRegions({collection: geom, reducer: 'first', scale: z}); #.getInfo();


def runLTversionsHelper2(feature):
    return feature.set('index', indexName).set('params', runParams[index]).set('param_num', index);

def runLTversionsHelper(param):
    # this statment finds the index of the parameter ation being used
    index = runParams.indexOf(param)

    # here we select the indice image on which to run LandTrendr
    runParams[index]["timeseries"] = ic.select([indexName])

    # run LandTrendr

    lt = ee.Algorithms.TemporalSegmentation.LandTrendr(runParams[index])

    # select the segmenationdata from LandTrendr

    ltlt = lt.select(['LandTrendr'])

    # slicde the LandTrendr data into sub arrays

    yearArray = ltlt.arraySlice(0, 0, 1).rename(['year'])

    sourceArray = ltlt.arraySlice(0, 1, 2).rename(['orig'])

    fittedArray = ltlt.arraySlice(0, 2, 3).rename(['fitted'])

    vertexMask = ltlt.arraySlice(0, 3, 4).rename(['vert'])

    rmse = lt.select(['rmse'])

    # place each array into a image stack one array per band

    lt_images = yearArray.addBands(sourceArray).addBands(fittedArray).addBands(vertexMask).addBands(rmse)

    # extract a LandTrendr pixel times a point

    getpin2 = getPoint2(id_points, lt_images,20);  # add scale 30 some points(cluster_id 1800 for example) do not extract lt data.I compared the before change output with the after the chagne output and the data that was in both datasets matched.compared 1700 to 1700...

    # maps over a feature collection that holds the LandTrendr data and adds attributes: index, params and param number.

    attriIndexToData = getpin2.map(runLTversionsHelper2)

    return attriIndexToData;

def runLTversions(ic, indexName, id_points):

    # here we map over each LandTrendr parameter ation, appslying eachation to the abstract image

    printer = runParams.map(runLTversionsHelper)

    return printer;


#exports.runLTversions = runLTversions;


def mergeLToutput(lt_outputs):
    # empty iable to a merged feature collection featCol;

    # loop over each feature collection and merges them into one
    for i in lt_outputs:
        if i == 0:
            featCol = lt_outputs[0];
        elif i > 0 :
            featCol = featCol.merge(lt_outputs[i]);

    return featCol;


#exports.mergeLToutputs = mergeLToutputs;

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 05 Optimized Imager # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
def printer_helper_two(img):
    out = img.updateMask(cluster_mask).set('system:time_start', img.get('system:time_start'));
    return out;

def printer_helper(feat):
    # changes feature object to dictionary
    dic = ee.Feature(feat).toDictionary();

    # calls number value from dictionary feature key, maxSegments.

    maxSeg = dic.getNumber('maxSegments');

    # calls number value from dictionary feature key, spikeThreshold.

    spikeThr = dic.getNumber('spikeThreshold');

    # calls number value from dictionary feature  key, "recoveryThreshold".

    recov = dic.getNumber('"recoveryThreshold"');

    # calls number value from dictionary feature key, "pvalThreshold"d.

    pval = dic.getNumber('"pvalThreshold"d');

    # LandTrendr parameter dictionary template.

    runParamstemp = {
        "timeseries": ee.ImageCollection([]),
        "maxSegments": maxSeg,
        "spikeThreshold": spikeThr,
        "vertexCountOvershoot": 3,
        "preventOneYearRecovery": True,
        "recoveryThreshold": recov,
        "pvalThreshold": pval,
        "bestModelProportion": 0.75,
        "minObservationsNeeded": maxSeg
    };

    # get cluster ID from dictionary feature as a number

    cluster_id = ee.Number(dic.get('cluster_id')).float();

    # creates a mask keep pixels for only a single cluster - changed for something more simple cluster_mask = cluster_image.eq(cluster_id).selfMask();

    # blank maskcol;

    # maps over image collection applying the mask to each image
    maskcol = ic.map(printer_helper_two)


    # apply masked image collection to LandTrendr parameter dictionary
    runParamstemp["timeseries"] = maskcol;

    # Runs LandTrendr

    lt = ee.Algorithms.TemporalSegmentation.LandTrendr(runParamstemp).clip(aoi);  # .select(0) #.unmask();

    # return LandTrendr image collection run to list.
    return lt;

# Run the versions of LT we selected, uses masks to run the correct version for the SNIC patches in a given kmeans cluster
# input args are the index tables above and the associated imageCollection
def printerFunc(fc, ic, cluster_image, aoi):

    output = fc.map(printer_helper)
    # this might be a little redundant but its a way to deal with the map statements
    return output;

#exports.printerFunc = printerFunc;


def filterTable(pt_list, index):
    return pt_list.filter(ee.Filter.eq('index', index));


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

    SNICimagery = SNICoutput.toInt32() #.reproject({crs: 'EPSG:4326', scale: 30}); # previously snicImagery

    SNICmeans = SNICpixels.toInt32().clip(aoi) # previously SNIC_means_image

    # try just creating some random points
    snicPts = ee.FeatureCollection.randomPoints(
        region= aoi,
        points= random_pts,
        seed= 10
    )

    # do the sampling
    snicPts = samplePts(snicPts, SNICimagery);

    return ee.List([snicPts, SNICimagery]);
    # return null

#exports.snic01 = snic01;

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 02 kMeans # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
def kmeans02_1(snicPts, SNICimagery, aoi, min_clusters, max_clusters):
    # take the snic outputs from the previous steps and thentrain and run a kmeans model

    snicKmeansImagery = ee.Image(SNICimagery).select(["B1_mean", "B2_mean", "B3_mean", "B4_mean", "B5_mean", "B7_mean", "B1_1_mean", "B2_1_mean", "B3_1_mean","B4_1_mean", "B5_1_mean", "B7_1_mean", "B1_2_mean", "B2_2_mean", "B3_2_mean", "B4_2_mean", "B5_2_mean","B7_2_mean"])

    kMeansImagery = runKmeans(snicPts, min_clusters, max_clusters, aoi, snicKmeansImagery);

    kMeansPoints = selectKmeansPts(kMeansImagery, aoi);
    return kMeansImagery
    # return ee.List([kMeansImagery, kMeansPoints]);


def kmeans02_2(kmeans_imagery, aoi):

    kMeansPoints = selectKmeansPts(kmeans_imagery, aoi)

    return kMeansPoints;


#exports.kmeans02_1 = kmeans02_1
#exports.kmeans02_2 = kmeans02_2
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 03 abstractSampler # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
def rename_kmeans(feat):
    return feat.set('cluster_id', feat.get('cluster'))

def abstractSampler03_1(full_timeseries, kMeansPts, startYear, endYear):

    # rename the kmeans points dataset cluster col to cluster_id, that 's what the remaining scripts expect
    kMeansPts = kMeansPts.map(rename_kmeans)

    # add spectral indices to the annual ic
    images_w_indices = computeIndices(full_timeseries)

    # extract values from the composites at the points created in the kmeans step above

    spectralExtraction = runExtraction(images_w_indices, kMeansPts, startYear, endYear)

    # Select out the relevant fields
    abstractImageOutputs = spectralExtraction.select(['cluster_id', 'year', 'NBR', 'TCW', 'TCG', 'NDVI', 'B5'], None,False) #.sort('cluster_id') null and false are the old js arguments

    return abstractImageOutputs


#exports.abstractSampler03_1 = abstractSampler03_1;

def abstractSampler03_2(img_path, startYear, endYear):

    # this has to be called separately after the first half is dealt with outside GEE
    # replaces the manual creation of an imageCollection after uploading abstract images

    abstractImages = []
    yearlist = list(range(startYear,endYear))
    for y in yearlist:
        img = ee.Image(img_path+y.toString())
        abstractImages.append(img)

    # this is the primary input to the 04 script
    abstractImagesIC = ee.ImageCollection.fromImages(abstractImages);
    return abstractImagesIC;


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
    abstractImagesIC = abstractImagesIC.select(['b1', 'b2', 'b3', 'b4', 'b5'], indices) # changed to uppercase

    for i in indices:

        # this calls the printer function that runs different versions of landTrendr
        multipleLToutputs = runLTversions(abstractImagesIC, indices[i], id_points)

        # this merges the multiple LT runs
        combinedLToutputs = mergeLToutputs(multipleLToutputs)

        # then export the outputs - the paramater selection can maybe be done in GEE at some point but its
        # a big python script that needs to be translated into GEE
        task = ee.batch.Export.table.toDrive(
            collection= combinedLToutputs,
            description= "LTOP_" + place + "_abstractImageSample_lt_144params_" + indices[i] + "_c2_revised_ids",
            folder= "LTOP_" + place + "_abstractImageSamples_c2_revised_ids",
            fileFormat= 'CSV'
        )
    return 0

#exports.abstractImager04 = abstractImager04;

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# # # # # # # # # # # # # # # # 05 Optimized Imager # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # /
# cast the feature collection(look up table) to list so we can filter and map it.
def optimizedImager05(table, annualSRcollection, kmeans_output, aoi):
    lookUpList = table.toList(table.size())

    # transformed Landsat surface reflectance image collection - this likewise would need to be changed for more indices
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