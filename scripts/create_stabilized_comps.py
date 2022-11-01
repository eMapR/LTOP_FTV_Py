######################################################################################################### 
##                                                                                                    #\\
##                             SERVIR Composites temporal stabilization                               #\\
##                                                                                                    #\\
#########################################################################################################
# date: 2022-06-01
# author: Ben Roberts-Pierel | robertsb@oregonstate.edu
#         Peter Clary        | clarype@oregonstate.edu
#         Robert Kennedy     | rkennedy@coas.oregonstate.edu
#         
# website: https:#github.com/eMapR/LT-GEE
# This script requires some user-defined params as well as outputs of the LTOP LandTrendr process. 
# 1. cluster_image - this is the output of the kmeans algorithm (LTOP 02)
# 2. ltop_output - this is the final output of LTOP, a multiband image with the LandTrendr vertex breakpoints
# 3. table - these are the selected versions of LandTrendr that are used in the LTOP generation process 
# 4. dest_folder - this should be created and set by the user. This will be where the stabilized composites end up. Do not add a slash, its done for you below
import ee  
import pandas as pd 
import ltop 
import LandTrendr as ltgee
import yaml 

try: 
	ee.Initialize()
except Exception as e: 
	ee.Authenticate()
	ee.Initialize()


#############################/
##########Bring in the LTOP outputs#######
#############################/

def prep_inputs(ltop_bps,selected_lt_params,ic,cluster_image,band_names,min_obvs=11): 
    '''
    Take outputs of LTOP process and create inputs required for LTFit and run LTFit
    '''
    #prep the breakpoints for LT-fit. These are the primary outputs of the LTOP process
    breakpoints = ltop.prepBreakpoints(ltop_bps) 

    #run lt fit 
    #this output will be an image where each band is a fitted value of time series for that band
    #NOTE that this is pulling from the LTOP selected LT outputs for the spikeThreshold LT param 
    lt_fit_output = ltop.runLTfit(selected_lt_params,ic,breakpoints,cluster_image,min_obvs) 

    return lt_fit_output

#############################/
#/Reconfigure the LT output to match SERVIR composites##
#############################/
#this section could likely be rewritten to be more efficient/use less for loops but should currently be working
def rename_helper(y,modifier): 
    return ee.String(y).cat(modifier)

def rename_bands(img,modifier,start_names):
    end_names = start_names.map(lambda y: rename_helper(y,modifier)) 
    return img.select(start_names,end_names)

def rename_lt_fit(name,lt_fit_output,years): 
    #this is an array image with a time series
    nm = ee.String(name)
    img = lt_fit_output.select(nm)
    return rename_bands(img.arrayFlatten([years],nm).set('source_band',nm),ee.String('_').cat(nm))

def match_LT_to_servir(band_names,lt_fit_output,*args):
    '''
    Reconfigure the LT outputs (band names etc.) to look like the SERVIR composites. This section could likely be rewritten to be more efficient/use 
    less for loops but should currently be working
    '''
    args = args[0]
    #make an arry and fill with years from the startYear to the endYear and convert them to string
    years = [str(y) for y in range(args['startYear'],args['endYear']+1)] 

    #make a list of names that match the bands in the output of lt fit - previously came from servir comps at the start of the script 
    new_names = band_names.map(lambda x: ee.String(x).cat(ee.String('_fit'))) 

    #convert array images to a multiband image. This will end up as a list of images. 
    FTVstacks = new_names.map(lambda x: rename_lt_fit(x,lt_fit_output,years))
    return FTVstacks

def bandToCollection_helper(b,bands,collection): 
    band_name = ee.String(bands.get(ee.Number(b).subtract(1))) 
    img = ee.Image(collection.select(band_name)) 
    year = band_name.slice(0,4) 
    return img.set('year',ee.Number.parse(year)) 

def bandToCollection(collection):
    bands = collection.bandNames()
    dayCounter = ee.List.sequence(1, bands.size())    
    newCollection = dayCounter.map(lambda x: bandToCollection_helper(x,bands,collection))
    return newCollection

def output_naming_helper2(b):
    #the bands are set up to have a four digit year in front of the band name so just remove that
    return ee.String(b).slice(5)

def output_naming_helper(img): 
    bands = img.bandNames() 
    new_bands = bands.map(output_naming_helper2)
    #for some reason the default data type is double precision float - change that to something smaller 
    return img.select(bands,new_bands).toInt16()

def rebuild_image_collection(num_bands,FTVstacks):
    #initialize an empty container for the imageCollections 
    collections = [] 

    lower = (ee.Number(num_bands).subtract(1)).getInfo() 
    upper = ee.Number(num_bands).getInfo() 

    for i in range(upper): 
        #convert the multiband images to imageCollections 
        collections.append(ee.ImageCollection(bandToCollection(ee.Image(FTVstacks.get(i)))))#get(indices[i])))))


    #this for loop could maybe be replaced with the iterate function? 
    #create an initialization imageCollection - this will default to the blue band 
    output = collections[0]
    #snip off the first collection (blue) because its already in the start
    collections = ee.List(collections).slice(1)
    for i in range(lower): 
        #use the combine function to stick each band/time series onto the previous 
        output = output.combine(ee.ImageCollection(collections.get(i)))#.get(indices[i]))) 

    #now remove the year to mimic the band naming structure of the servir composites
    output = output.map(output_naming_helper)

    #now sort them because they come out of the map in a weird order
    output = output.sort('year') 
    return output

def export_imgs(output_collection,*args): 
    '''
    Generate GEE tasks to export each image in the imageCollection. This could also be set up to export an imageCollection instead of individual images but its 
    supposed to mimic the setup of the SERVIR composites. 
    '''
    for i in range(args['startYear'],args['endYear']+1): 
    
        out_img = output_collection.filter(ee.Filter.eq('year',i)).first().clip(args['aoi'])
        yr_str = ee.Number(i).format().getInfo() 
    
        task = ee.batch.Export.image.toAsset(
            image = out_img, 
            description = "servir_"+yr_str+"_stabilized_"+args['place'], 
            assetId = args['assetsChild']+"/servir_"+yr_str+"_stabilized_"+args['place'], 
            region = args['aoi'], 
            scale = 30, 
            maxPixels = 1e13 
            )
        task.start()
        return None 

def get_asset_names(assets_dir,search_term): 
        '''
        For runs that generate multiple outputs that cover the overall ROI get all of those and splice them 
        back together into one image/fc. 
        '''
        #the output is like: {'assets':[{dict with metadata on each asset}]}
        assets = ee.data.listAssets({'parent':assets_dir})
        #subset the assets to just their names that contain search_term
        assets = [a['name'] for a in assets['assets'] if search_term in a['name']]
        return assets

def main(aoi,*args): 
    '''
    Invoke the process to generate stabilized composites from an input dataset. Defaults to (and expects) the SERVIR composites and their naming/band structure. 
    Script will output or generate one task for each year (composite) in the time series. This time series length is dictated by the startYear and endYear args in the 
    params.py file. 
    '''
    args = args[0]

    if args['run_times'] == 'multiple': 
        #we need to combine multiple outputs in the instance that's how they're formatted
        cluster_image = ee.ImageCollection.fromImages(get_asset_names(args['assetsRoot']+args['assetsChild'],'KMEANS_cluster_image')).mosaic()
        ltop_output = ee.ImageCollection.fromImages(get_asset_names(args['assetsRoot']+args['assetsChild'],'Optimized')).mosaic()
        table = ee.FeatureCollection(ee.List(get_asset_names(args['assetsRoot']+args['assetsChild'],'LT_params_tc'))).flatten()

    elif args['run_times'] == 'single': 
        #get the necessary inputs from LTOP process- USE for a single geometry run
        cluster_image = ee.Image(args["assetsRoot"] +args["assetsChild"] + "/LTOP_KMEANS_cluster_image_" + str(args["randomPts"]) + "_pts_" + str(args["maxClusters"]) + "_max_" + str(args["minClusters"]) + "_min_clusters_" + args["place"] + "_c2_" + str(args["startYear"]))
        ltop_output = ee.Image('Optimized_LT_'+str(args['startYear'])+'_start_'+ args['place']+'_all_cluster_ids_tc')
        table = ee.FeatureCollection(args['outfile'])

    #build imageCollection of SERVIR composites 
    servir_ic = ltop.buildSERVIRcompsIC(args['startYear'],args['endYear']) 
    #TODO this could probably be changed for an instance with single or multiple runs 
    servir_ic = servir_ic.filterBounds(aoi) 
    #get a list of all the servir bands
    band_names = servir_ic.first().bandNames() 
    num_bands = band_names.size() 
    
    #call functions
    lt_fit_outputs = prep_inputs(ltop_output,table,servir_ic,cluster_image,band_names,min_obvs=11)
    new_collection = match_LT_to_servir(band_names,lt_fit_outputs,args)
    export_collection = rebuild_image_collection(num_bands,new_collection)
    #should return None 
    output = export_imgs(export_collection,args)

if __name__ == '__main__': 
    aoi = ee.FeatureCollection("projects/servir-mekong/hydrafloods/CountryBasinsBuffer").geometry()

    with open("config.yml", "r") as ymlfile:
        cfg = yaml.safe_load(ymlfile)
        main(aoi,cfg)