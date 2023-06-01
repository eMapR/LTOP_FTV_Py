from run_ltop_complete import RunLTOPFull,parse_params
# import params
import ee
import yaml

try: 
	ee.Initialize()
except Exception as e: 
	ee.Authenticate()
	ee.Initialize()

'''
Example runs of the LandTrendr Optimization (LTOP) workflow. See associated documentation for more
information on the process and outputs. This script features examples for running one large ROI or iterating
through parts of a featureCollection. In this instance, you run each chunk all the way through the LTOP workflow. 
'''

if __name__ == '__main__':

    #example for single run (one ROI)
    print('running a single')
    #aoi = ee.FeatureCollection("projects/servir-mekong/hydrafloods/CountryBasins_10k").geometry()
    aoi = ee.FeatureCollection("users/clarype/cambodia").geometry()   
    with open("config.yml", "r") as ymlfile:
        cfg = yaml.safe_load(ymlfile)
        cfg = parse_params(aoi,cfg) #TODO decide what to do with the AOI
        single_example = RunLTOPFull(cfg,sleep_time=30)
        single_example.runner()
        
    #################################################################################
    #example for running multiple geometries
    # print('running multiple geometries')
    # # grid = ee.FeatureCollection('projects/ee-ltop-py/assets/ltop_large_scale_runs/clipped_test_grid')
    # # grid_list = grid.toList(grid.size())
    # filter_list = ['Cambodia','Burma','Thailand','Laos','Vietnam']
    # countries = ee.FeatureCollection("USDOS/LSIB/2017").filter(ee.Filter.inList('COUNTRY_NA',filter_list))
    # #for the servir aoi there are some areas that are outside the main countries we want to run because of watershed boundaries. Add those in here. 
    # poly1 = ee.FeatureCollection('projects/ee-ltop-py/assets/ltop_large_scale_runs/diff_poly1_west').set('COUNTRY_NA','poly1_west')
    # poly2 = ee.FeatureCollection('projects/ee-ltop-py/assets/ltop_large_scale_runs/diff_poly2_north').set('COUNTRY_NA','poly2_north')
    # poly3 = ee.FeatureCollection('projects/ee-ltop-py/assets/ltop_large_scale_runs/diff_poly3_east').set('COUNTRY_NA','poly3_east')
    # countries = countries.merge(poly1).merge(poly2).merge(poly3)
    # country_list = countries.toList(countries.size())
    # with open("config.yml", "r") as ymlfile:
    #     cfg = yaml.safe_load(ymlfile)
    #     param_fp = cfg['param_scoring_inputs']

    #     for i in range(countries.size().getInfo()): 
    #         #just try adding a small buffer so we can 'feather' the boundaries for multi-country options 
    #         input_aoi = ee.Feature(country_list.get(i)).geometry().buffer(1000)
    #         #modify the params file inputs
    #         # place = 'multiple_'+ee.Number(ee.Feature(country_list.get(i)).get('id')).format().getInfo()
    #         place = 'multiple_'+ee.Feature(country_list.get(i)).get('COUNTRY_NA').getInfo()
    #         print(place)
    #         if i == 0: 
    #             cfg.update({'place':place})
    #             revised = parse_params(input_aoi,cfg)
    #         elif i > 0: 
    #             print('doing second')
    #             revised.update({'place':place})
    #             revised.update({'param_scoring_inputs':param_fp})
    #             revised = parse_params(input_aoi,revised)
                
    #         multiple_example = RunLTOPFull(revised,sleep_time = 30)
    #         multiple_example.runner()
