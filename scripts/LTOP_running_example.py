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
    # aoi = ee.FeatureCollection("USDOS/LSIB/2017").filter(ee.Filter.eq('COUNTRY_NA','Cambodia')).geometry()
    aoi = ee.Geometry.Polygon(
        [[[105.21924736250195, 14.414700359899358],
          [105.21924736250195, 12.212492266993609],
          [107.62525322187695, 12.212492266993609],
          [107.62525322187695, 14.414700359899358]]])

    with open("config.yml", "r") as ymlfile:
        cfg = yaml.safe_load(ymlfile)
        cfg = parse_params(aoi,cfg) #TODO decide what to do with the AOI
        single_example = RunLTOPFull(cfg,sleep_time=30)
        single_example.runner()
        
    #################################################################################
    #example for running multiple geometries
    # grid = ee.FeatureCollection('projects/ee-ltop-py/assets/ltop_large_scale_runs/clipped_test_grid')
    # grid_list = grid.toList(grid.size())
    # with open("config.yml", "r") as ymlfile:
    #     cfg = yaml.safe_load(ymlfile)
    #     param_fp = cfg['param_scoring_inputs']

    #     for i in range(grid.size().getInfo()): 
    #         input_aoi = ee.Feature(grid_list.get(i)).geometry()
    #         #modify the params file inputs
    #         place = 'grid_'+ee.Number(ee.Feature(grid_list.get(i)).get('id')).format().getInfo()
    #         if i == 0: 
    #             cfg.update({'place':place})
    #             revised = parse_params(input_aoi,cfg)
    #         elif i > 0: 
    #             print('doing secnod')
    #             revised.update({'place':place})
    #             revised.update({'param_scoring_inputs':param_fp})
    #             revised = parse_params(input_aoi,revised)
                
    #         multiple_example = RunLTOPFull(revised,sleep_time = 30)
    #         multiple_example.runner()