import ee 
import params
import time 
import pandas as pd 
import ltop 
import lt_params
import run_SNIC_01 as runSNIC
import run_kMeans_02_1 as kmeans_1
import run_kMeans_02_2 as kmeans_2
import abstract_sampling_03 as ab_img
import abstract_imager_04 as run_lt_pts
import ltop_lt_paramater_scoring_01 as param_scoring
import generate_LTOP_05 as make_bps
import os 

"""
This script is intended to run the entire LandTrendr Optimization (LTOP) workflow for paramater 
selection of the LandTrendr algorithm (Kennedy et al, 2014; 2018). The process relies on a series of scripts that: 
1. spatially segment the target aoi based on spectracl characteristics of an underlying dataset 
2. Cluster those spatial segments (patches) into spectrally similar clusters. This step uses the kmeans algorithm
3. Spectral information and associated cluster information is stored in abstract images to decrease storage, computation and run time
4. LandTrendr is run for every cluster (group of patches) on the landscape and a paramater scoring regime is carried out to select the best
'version' of LandTrendr for that target land cover/land use class 
5. Selected verions of LT are run on all of the clusters and the final image is put back together. The final output are the breakpoints that 
one expects from a standard LandTrendr run. 

Dependencies: 
The required scripts can be cloned or forked from GitHub at: XXXXXXXXXXXXX
For more information on the process and the theory behind it see the documentation on GitHub at: XXXXXXXXXXXXXXXXXXXXXXXX

Notes: 
This script is set up so that it will run through all of the steps in the LTOP workflow, waiting in between steps for the previous output to finish
generating before going on to the next step. Depending on the area you are running, this could take a long time (days). This is why it is built 
in a .py script and not a Jupyter Notebook. There is an associated Jupyter Notebook for doing small test areas located on GitHub at: XXXXXXXXXXXXXXXXXXXX. 
The intermediate outputs will be generated in a user specified assets folder on your GEE account and the location of this folder can be 
specified in the params.py file under assetsRoot and assetsChild. 
"""

class RunLTOPFull(object): 
    '''
    Run the entire LTOP workflow to select a param set for a given aoi used to run LandTrendr.
    This implements logic to run the required steps, allowing for wait times between running of functions and 
    generation of outputs. 
    '''
    
    def __init__(self,*args,max_time=1200): 
        self.args = args[0] #call args as params.params externally
        self.max_time = max_time
    
    def check_for_wd(self): 
        '''
        Look in the assets folders to see if the intended directory is there. 
        If its not then make it. 
        '''
        wd = self.args['assetsRoot']+self.args['assetsChild']
        folders = ee.data.listAssets({'parent':self.args['assetsRoot']})
        folders = [i for i in folders['assets'] if i['type'] == 'FOLDER']
        target = [i for i in folders if i['name'] == wd]
        if len(target) == 0: 
            print(f'The working directory {wd} does not exist, creating...')
            ee.data.createAsset({'type':'FOLDER'},wd)
        else: 
            print('The working directory already exists, proceeding...')

    def check_task_status(self,task_id): 
        '''
        Check on the status of a GEE batch task submitted to GEE servers. Input to this function should be a dictionary that is formatted 
        like the output of task.status()
        '''
        #for some reason GEE defaults this to a list with a dictioanary as its only item
        task_status = ee.data.getTaskStatus(task_id)[0]

        return task_status['state']
    
    def check_assets_presence(self,assets_list): 
        '''
        For the functions that generate more than one job/task, check the destination assets folder
        to see when all the assets are done. There is probably a more efficient way to do this.
        '''
        #the output is like: {'assets':[{dict with metadata on each asset}]}
        assets = ee.data.listAssets({'parent':self.args['assetsRoot']+self.args['assetsChild']})
        #subset the assets to just their names that contain 'synthetic'
        assets = [a['name'] for a in assets['assets']] #if 'synthetic' in a['name']]
        #now check if all of our years are there- returns True if yes, False if no
        results = all(e in assets for e in assets_list)
        if results: 
            return True 
        else: 
            return False 

    def runner(self): 
        self.check_for_wd()
        #1. run SNIC
        #first check if snic has already been run- there should be a better way to do this
        snic_pts_path= self.args["assetsRoot"]+self.args["assetsChild"]+"/LTOP_SNIC_pts_"+self.args["place"]+"_c2_"+str(self.args["randomPts"])+"_pts_"+str(self.args["startYear"])
        snic_img_path = self.args["assetsRoot"]+self.args["assetsChild"]+"/LTOP_SNIC_imagery_"+self.args["place"]+"_c2_"+str(self.args["randomPts"])+"_pts_"+str(self.args["startYear"])

        proceed = self.check_assets_presence([snic_pts_path,snic_img_path])
        #TODO this is currently an all or nothing thing, it will try to create both snic outputs if one is missing
        if not proceed: 
            print('SNIC assets do not yet exist, creating...')
            status1,status2 = runSNIC.generate_snic_outputs(self.args)
            while True: 
                ts_1 = self.check_task_status(status1['id'])
                ts_2 = self.check_task_status(status2['id'])
                if (ts_1 == 'COMPLETED') & (ts_2 == 'COMPLETED'): 
                    print('The snic tasks are now complete')
                    time.sleep(10)
                    break
                elif (ts_1 == 'FAILED') | (ts_1 == 'CANCELLED'): 
                    print('The snic points generation failed')
                    break
                elif (ts_2 == 'FAILED') | (ts_2 == 'CANCELLED'): 
                    print('The snic image generation failed')
                    break
        else: 
            print('SNIC assets already exist or are running, proceeding...')
        
        #now check kmeans 
        kmeans_img_path = self.args["assetsRoot"] +self.args["assetsChild"] + "/LTOP_KMEANS_cluster_image_" + str(self.args["randomPts"]) + "_pts_" + str(self.args["maxClusters"]) + "_max_" + str(self.args["minClusters"]) + "_min_clusters_" + self.args["place"] + "_c2_" + str(self.args["startYear"])
        kmeans_pts_path = self.args['assetsRoot']+self.args['assetsChild']+'/LTOP_KMEANS_stratified_points_'+str(self.args['maxClusters'])+'_max_'+str(self.args['minClusters'])+'_min_clusters_'+self.args['place']+'_c2_'+str(self.args['startYear'])
        proceed = self.check_assets_presence([kmeans_img_path])
        if not proceed: 
            print('kmeans image does not yet exist, creating...')
            km_status = kmeans_1.generate_kmeans_image(self.args)
            while True: 
                km_test = self.check_task_status(km_status['id'])
                if km_test == 'COMPLETED':
                    print('The kmeans image was successfully generated')
                    time.sleep(10)
                    break
                elif (km_test == 'FAILED') | (km_test == 'CANCELLED'): 
                        print('The generation of the kmeans image failed')
                        break
        else: 
            print('kmeans image exists, proceeding to kmeans pts...')
        
        proceed = self.check_assets_presence([kmeans_pts_path])

        if not proceed: 
            print('kmeans points do no yet exist, creating...')
            km_pts_status = kmeans_2.generate_kmeans_pts(self.args)
            while True: 
                km_pts_test = self.check_task_status(km_pts_status['id'])
                if km_pts_test == 'COMPLETED':
                    print('The kmeans points were successfully generated')
                    time.sleep(10)
                    break
                elif (km_pts_test == 'FAILED') | (km_pts_test == 'CANCELLED'): 
                        print('The generation of the kmeans image failed')
                        break
        else: 
            print('The kmeans points have been generated, proceeding...')
        
        #3. abstract image generation
        #make a list of abstract images we're looking for. This is so that it is not made again
        #everytime we go through the while loop 
        #TODO this needs to have logic added to also catch/not rerun the grid points asset 
        abs_imgs_list = []
        for year in range(self.args['startYear'],self.args['endYear']+1): 
            abs_imgs_list.append(self.args['assetsRoot']+self.args['assetsChild'] + "/synthetic_image_" + str(year))
        start_time = time.time()
        #while True: 
            #the logic here is a little different than previous steps because there is an 
            #abstract image for every year in the time series and they are internally generated tasks
        proceed = self.check_assets_presence(abs_imgs_list)
        if not proceed: 
            print('Abstract images do not exist, starting abstract image generation')
            ab_img.create_abstract_imgs(self.args)
            while True: 
                check_status = self.check_assets_presence(abs_imgs_list)
                #add a little break on each iteration so it doesn't keep hitting google's servers
                time.sleep(10)
                if check_status: 
                    print('The abstract images are done generating, proceeding...')
                    break 
                elif (time.time() - start_time) > self.max_time: 
                    print(f'The abstract image generation took longer than {self.max_time}')
                    print('The process stopped. Check for errors or increase max_time arg (defaults to 1200 seconds)')
                    break
                else: 
                    pass
        else: 
            print('The abstract images already exist, proceeding to param selection')
        
        #4. run the extraction of spectral information from abstract image points/kmeans points
        #check if the 04 csv output already exists
        #TODO this should be grouped with the other file names in a more central location
        #TODO this is currently hardcoded and won't change anything if changed elsewhere or added to params
        indices = ['NBR', 'NDVI', 'TCG', 'TCW', 'B5']
        names = []
        for i in range(len(indices)): 
            names.append("LTOP_" + self.args['place'] + "_abstractImageSample_lt_144params_" + indices[i] + "_c2_selected"+".csv")
        
        #check if the indices files have already been generated and sent to GCS bucket
        proceed = ltop.check_multiple_gcs_files(names,self.args['cloud_bucket'])
        if not proceed: #the files have not been generated
            print(f'The csv files for LT outputs do not exist, generating in {self.args["cloud_bucket"]}')
            run_lt_pts.run_LT_abstract_imgs(self.args)
            while True: 
                check_status = ltop.check_multiple_gcs_files(names,self.args['cloud_bucket'])
                if check_status: 
                    print('The csvs for LT outputs on abstract images are done')
                    break
                else: 
                    time.sleep(self.max_time/10) #TODO this time is somewhat arbitrary
        else: 
            print('The csv files of LT output already exist, proceeding...')
            #make sure the intended destination dir exists
            if not os.path.exists(self.args['param_scoring_inputs']): 
                os.mkdir(self.args['param_scoring_inputs'])
            out_fns = [self.args['param_scoring_inputs']+f for f in names]
            #trigger the download of the csv files from GCS bucket
            #TODO decide if this should just get everything in a specific folder
            #TODO add a check to not download if these files already exist
            ltop.download_multiple_from_bucket(self.args['cloud_bucket'],names,out_fns)
        
        #now check for the downloaded files
        while True: 
            if all(os.path.isfile(f) for f in out_fns): 
                print('Files are done downloading')
                break
            else: 
                time.sleep(self.max_time/10)

        #4.1 run the param selection process which happens in Python. 
        if os.path.isfile(self.args['outfile']): 
            print('The selected params already exist')

        else: 
            print('Starting the param scoring regime')
            #check if the output dir is there and if not create it
            out_dir = os.path.split(self.args['outfile'])[0]
            if not os.path.exists(out_dir): 
                os.mkdir(out_dir)
            param_scoring.generate_selected_params(self.args) 
            #check when this thing is done
            while True: 
                check_status = os.path.exists(self.args['outfile'])
                if check_status: 
                    print('The param selection process has concluded, move to upload')
                    break
                else: 
                    #this time is somewhat arbitrary and for a full run will take some hours unless we improve this script 
                    time.sleep(self.max_time) 

        #check if the selected params have been uploaded to GCS
        selected_params_fn = os.path.split(self.args['outfile'])[1]
        if ltop.check_single_gcs_file(selected_params_fn,self.args['cloud_bucket']): 
            print('selected params already exist')
        else: 
            print('Uploading selected params to GCS')
            
            #just take the file name as the GCS bucket name and upload selected params
            ltop.upload_to_bucket(os.path.split(self.args['outfile'])[1],self.args['outfile'],self.args['cloud_bucket'])
            time.sleep(10) #TODO change times? 
        
        #now create an asset from the uploaded csv over in GEE
        #check if an asset exists - for the naming, :-4 is just stripping the ext
        proceed = self.check_assets_presence([self.args['assetsRoot']+self.args['assetsChild']+'/'+selected_params_fn[:-4]])
        if proceed: 
            print('The asset of selected params already exists')
        else: 
            print("Creating selected params asset...")
            ltop.create_gee_asset_from_gcs(selected_params_fn[:-4],f"gs://{self.args['cloud_bucket']}/{selected_params_fn}",self.args['assetsRoot']+self.args['assetsChild'])
            while True: 
                check_status = self.check_assets_presence([self.args['assetsRoot']+self.args['assetsChild']+selected_params_fn[:-4]])
                if check_status: 
                    print('The selected params have been successfully uploaded')
                    break
                else: 
                    time.sleep(10) #TODO check time 
        bps_fn = 'Optimized_LT_'+str(self.args['startYear'])+'_start_'+self.args['place']+'_all_cluster_ids_tc'
        proceed = self.check_assets_presence([self.args['assetsRoot']+self.args['assetsRoot']+'/'+bps_fn])
        if not proceed: 
            print('The final breakpoints do not exist, creating')
            lt_vertices_status = make_bps.generate_LTOP_breakpoints(self.args)
            while True:
                check_status = self.check_task_status(lt_vertices_status['id']) 
                if check_status == 'COMPLETED': 
                    print('The optimization process is complete, please check your final output')
                    break
                elif (check_status == 'FAILED') | (check_status == 'CANCELLED'): 
                    print('The generation of the final output failed')
                    break            
                else: 
                    #this time is somewhat arbitrary and should be increased for a real run
                    time.sleep(30)
        else: 
            print('The final output breakpoints already exist')
        
# #run it- not sure if we want to run from this script or from somewhere else
# # if __name__ == '__main__': 
# #     main()
#max time is set this low just for testing 
test = RunLTOPFull(params.params,max_time = 1200)
test.runner()