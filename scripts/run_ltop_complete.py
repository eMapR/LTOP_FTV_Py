import ee 
import params
import time 
import ltop 
import run_SNIC_01 as runSNIC
import run_kMeans_02_1 as kmeans_1
import run_kMeans_02_2 as kmeans_2
import abstract_sampling_03 as ab_img
import abstract_imager_04 as run_lt_pts
import ltop_lt_paramater_scoring_01 as param_scoring
import generate_LTOP_05 as make_bps
import os 
import yaml 

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
class IncorrectConfigValError(Exception): 
    """
    Check the config file inputs to decide if we should run one or multiple geometries. In the case that the wrong arg is passed,
    raise an error. 
    """
    def __init__(self,run_times,message='The only valid args for run_times are multiple or single.'): 
        self.run_times = run_times
        self.message = message
        super().__init__(self.message)

def parse_params(aoi,*args): 
    '''
    Helper function to change the formatting of inputs from the params file to make them the correct dtype/object for running LTOP. Takes a yml file?
    '''
    args = args[0]
    #first deal with things that change when we run multiple geometries
    args.update({'place':str(args['place'])})

    if args['run_times'] == 'multiple': 
        out_fn = os.path.split(args['outfile'])[0]
        args.update({'param_scoring_inputs':os.path.join(args['param_scoring_inputs'],'output_04_'+args["place"]+'/')}) #TODO might not need this slash here or should be handled differently elsewhere
        args.update({'outfile':os.path.join(out_fn,f'LTOP_{args["place"]}_selected_LT_params_tc.csv')})
        args.update({'aoi':aoi})
    elif args['run_times'] == 'single': 
        args.update({'param_scoring_inputs':os.path.join(args['param_scoring_inputs'],'output_04_'+args["place"]+'/')}) #TODO not sure if this needs the slash there or not 
        args.update({'outfile':os.path.join(args['outfile'],f'LTOP_{args["place"]}_selected_LT_params_tc.csv')})
        args.update({'aoi':aoi})
    else: 
        raise(IncorrectConfigValError(args['run_times']))
    args.update({'startYear':int(args['startYear'])})
    args.update({'endYear':int(args['endYear'])})
    args.update({'seedSpacing':int(args['seedSpacing'])})
    args.update({'randomPts':int(args['randomPts'])})
    args.update({'image_source':str(args['image_source'])})
    args.update({'assetsRoot':str(args['assetsRoot'])})
    args.update({'assetsChild':str(args['assetsChild'])})
    args.update({'maxClusters':int(args['maxClusters'])})
    args.update({'minClusters':int(args['minClusters'])})
    args.update({'selectedLTparams':ee.FeatureCollection(args['assetsRoot']+args['assetsChild']+f'/LTOP_{args["place"]}_selected_LT_params_tc')})
    args.update({'njobs':int(args['njobs'])})
    args.update({'cloud_bucket':str(args['cloud_bucket'])})
    # only needed for medoid composites
    args.update({'startDate':str(args['startDate'])})
    args.update({'endDate':str(args['endDate'])})
    args.update({'masked':list(args['masked'])})
    return args

class RunLTOPFull(object): 
    '''
    Run the entire LTOP workflow to select a param set for a given aoi used to run LandTrendr.
    This implements logic to run the required steps, allowing for wait times between running of functions and 
    generation of outputs. 
    '''
    
    def __init__(self,*args,sleep_time=30): 
        self.args = args[0] #call args as params.params externally
        self.sleep_time = sleep_time
        self.gee_cwd = self.args['assetsRoot']+self.args['assetsChild']
    
    def check_for_wd(self): 
        '''
        Look in the assets folders to see if the intended directory is there. 
        If its not then make it. 
        '''
        # wd = self.gee_cwd
        folders = ee.data.listAssets({'parent':self.args['assetsRoot']})
        folders = [i for i in folders['assets'] if i['type'] == 'FOLDER']
        target = [i for i in folders if i['name'] == self.gee_cwd]
        if len(target) == 0: 
            print(f'The working directory {self.gee_cwd} does not exist, creating...')
            ee.data.createAsset({'type':'FOLDER'},self.gee_cwd)
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
        assets = ee.data.listAssets({'parent':self.gee_cwd})
        #subset the assets to just their names that contain 'synthetic'
        assets = [a['name'] for a in assets['assets']] #if 'synthetic' in a['name']]
        #now check if all of our years are there- returns True if yes, False if no
        results = all(e in assets for e in assets_list)
        if results: 
            return True 
        else: 
            return False 

    def run_check_SNIC(self): 
        """
        Run the SNIC algorithm and then wait to make sure it works and things are run correctly before proceeding. 
        """
        #double check that the intended output GEE directory exists
        self.check_for_wd()
        #1. run SNIC
        #first check if snic has already been run- there should be a better way to do this
        snic_pts_path = self.gee_cwd+"/LTOP_SNIC_pts_"+self.args["place"]+"_c2_"+str(self.args["randomPts"])+"_pts_"+str(self.args["startYear"])
        snic_img_path = self.gee_cwd+"/LTOP_SNIC_imagery_"+self.args["place"]+"_c2_"+str(self.args["randomPts"])+"_pts_"+str(self.args["startYear"])

        proceed = self.check_assets_presence([snic_pts_path,snic_img_path])
        #TODO this is currently an all or nothing thing, it will try to create both snic outputs if one is missing
        if not proceed: 
            print('SNIC assets do not yet exist, creating...')
            status1,status2 = runSNIC.generate_snic_outputs(self.args)
            while True: 
                ts_1 = self.check_task_status(status1['id'])
                ts_2 = self.check_task_status(status2['id'])
                time.sleep(self.sleep_time)
                if (ts_1 == 'COMPLETED') & (ts_2 == 'COMPLETED'): 
                    print('The snic tasks are now complete')
                    return True
                    # break
                elif (ts_1 == 'FAILED') | (ts_1 == 'CANCELLED'): 
                    print('The snic points generation failed')
                    return False
                    # break
                elif (ts_2 == 'FAILED') | (ts_2 == 'CANCELLED'): 
                    print('The snic image generation failed')
                    return False 
                    # break
        else: 
            print('SNIC assets already exist or are running, proceeding...')
            return True
    
    def run_check_kmeans(self):
        """
        Check if the SNIC outputs are done and then run kmeans, checking to see if those outputs are done for the next operation. 
        """
        #now check kmeans 
        kmeans_img_path = self.args["assetsRoot"] +self.args["assetsChild"] + "/LTOP_KMEANS_cluster_image_" + str(self.args["randomPts"]) + "_pts_" + str(self.args["maxClusters"]) + "_max_" + str(self.args["minClusters"]) + "_min_clusters_" + self.args["place"] + "_c2_" + str(self.args["startYear"])
        kmeans_pts_path = self.gee_cwd+'/LTOP_KMEANS_stratified_points_'+str(self.args['maxClusters'])+'_max_'+str(self.args['minClusters'])+'_min_clusters_'+self.args['place']+'_c2_'+str(self.args['startYear'])
        proceed = self.check_assets_presence([kmeans_img_path])
        if not proceed: 
            print('kmeans image does not yet exist, creating...')
            km_status = kmeans_1.generate_kmeans_image(self.args)
            while True: 
                km_test = self.check_task_status(km_status['id'])
                time.sleep(self.sleep_time)
                if km_test == 'COMPLETED':
                    print('The kmeans image was successfully generated')
                    break
                elif (km_test == 'FAILED') | (km_test == 'CANCELLED'): 
                        print('The generation of the kmeans image failed')
                        break
        else: 
            print('kmeans image exists, proceeding to kmeans pts...')
        
        #now check if the imagery is there, if it is then run the points 
        proceed = self.check_assets_presence([kmeans_pts_path])

        if not proceed: 
            print('kmeans points do no yet exist, creating...')
            km_pts_status = kmeans_2.generate_kmeans_pts(self.args)
            while True: 
                km_pts_test = self.check_task_status(km_pts_status['id'])
                time.sleep(self.sleep_time)
                if km_pts_test == 'COMPLETED':
                    print('The kmeans points were successfully generated')
                    return True 
                    #break
                elif (km_pts_test == 'FAILED') | (km_pts_test == 'CANCELLED'): 
                    print('The generation of the kmeans image failed')
                    return False 
                    # break
        else: 
            print('The kmeans points have been generated, proceeding...')
            return True 
    
    def run_check_abstract_images(self): 
        """
        Create abstract images that are used for data compression of the kmeans points. 
        One point for each kmeans cluster and the associated spectral information from input composites.
        """
        #3. abstract image generation
        #make a list of abstract images we're looking for. This is so that it is not made again everytime we go through the while loop 
        abs_imgs_list = []
        for year in range(self.args['startYear'],self.args['endYear']+1): 
            abs_imgs_list.append(self.gee_cwd + f"/{self.args['place']}_synthetic_image_" + str(year))
        #also add the grid points because otherwise this might cause an error
        abs_imgs_list.append(self.gee_cwd+f"/{self.args['place']}_abstract_images_point_grid")
        # start_time = time.time()
        #the logic here is a little different than previous steps because there is an 
        #abstract image for every year in the time series and they are internally generated tasks
        proceed = self.check_assets_presence(abs_imgs_list)
        if not proceed: 
            print('Abstract images do not exist, starting abstract image generation')
            ab_img.create_abstract_imgs(self.args)
            while True: 
                check_status = self.check_assets_presence(abs_imgs_list)
                #add a little break on each iteration so it doesn't keep hitting google's servers
                time.sleep(self.sleep_time)
                if check_status: 
                    print('The abstract images are done generating, proceeding...')
                    return True  
                # elif (time.time() - start_time) > self.max_time: #TODO we should take this out or change this to a different approach. 
                #     print(f'The abstract image generation took longer than {self.max_time*10}') #TODO find a better solution to this issue
                    # print('The process stopped. Check for errors or increase max_time arg (defaults to 1200 seconds)')
                    # break
                else: 
                    pass
        else: 
            print('The abstract images and point grid already exist, proceeding to param selection')
            return True 
    
    def run_check_spectral_extraction(self): 

        """
        Run the extraction of spectral information from abstract image points/kmeans points. This will be used in the next step(s) for param selection. 
        """
        #check if the 04 csv output already exists
        #TODO this is currently hardcoded and won't change anything if changed elsewhere or added to params
        indices = ['NBR', 'NDVI', 'TCG', 'TCW', 'B5']
        names = []
        for i in range(len(indices)): 
            names.append("LTOP_" + self.args['place'] + "_abstractImageSample_lt_144params_" + indices[i] + "_c2_selected"+".csv")
        #build the file names list so regardless of whether we need to generate or not it won't throw an error 
        out_fns = [self.args['param_scoring_inputs']+f for f in names]
        #check if the indices files have already been generated and sent to GCS bucket
        proceed = ltop.check_multiple_gcs_files(names,self.args['cloud_bucket'])
        if not proceed: #the files have not been generated
            print(f'The csv files for LT outputs do not exist, generating in {self.args["cloud_bucket"]}')
            run_lt_pts.run_LT_abstract_imgs(self.args)
            while True: 
                check_status = ltop.check_multiple_gcs_files(names,self.args['cloud_bucket'])
                time.sleep(self.sleep_time)
                if check_status: 
                    print('The csvs for LT outputs on abstract images are done')
                    if not os.path.exists(self.args['param_scoring_inputs']): 
                        os.mkdir(self.args['param_scoring_inputs'])
                    #trigger the download of the csv files from GCS bucket   
                    #assumes we've generated the files and the dest local directory exists
                    print('Downloading csv files from GCS')
                    ltop.download_multiple_from_bucket(self.args['cloud_bucket'],names,out_fns)
                    return True 
                    # break
                else: 
                    time.sleep(self.sleep_time) #TODO this time is somewhat arbitrary
        else: 
            print('The csv files of LT output already exist, proceeding...')
            #make sure the intended destination dir exists
            if not os.path.exists(self.args['param_scoring_inputs']): 
                os.mkdir(self.args['param_scoring_inputs'])
            #trigger the download of the csv files from GCS bucket
            #TODO decide if this should just get everything in a specific folder
            if all (os.path.isfile(f) for f in out_fns): 
                print('The csv of params have already been downloaded')
                return True 
            else: 
                print('The csvs of params have not been downloaded, downloading...')
                ltop.download_multiple_from_bucket(self.args['cloud_bucket'],names,out_fns)
                return True 
        
    def run_check_param_selection(self):
        """
        Run selection of LT params. See LTOP documentation and associated Google Slides for more information on how this process works. 
        """
        indices = ['NBR', 'NDVI', 'TCG', 'TCW', 'B5']
        names = []
        for i in range(len(indices)): 
            names.append("LTOP_" + self.args['place'] + "_abstractImageSample_lt_144params_" + indices[i] + "_c2_selected"+".csv")
        out_fns = [self.args['param_scoring_inputs']+f for f in names]
        #now check for the downloaded files
        while True: 
            if all(os.path.isfile(f) for f in out_fns): 
                print('Files are done downloading')
                break
            else: 
                time.sleep(self.sleep_time)

        #4.1 run the param selection process 
        if os.path.isfile(self.args['outfile']): 
            print('The selected params already exist')
            return True 
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
                time.sleep(self.sleep_time)
                if check_status: 
                    print('The param selection process has concluded, move to upload')
                    break
                else: 
                    #this time is somewhat arbitrary and for a full run will take some hours unless we improve this script 
                    time.sleep(self.sleep_time) 
        #check if the selected params have been uploaded to GCS
        selected_params_fn = os.path.split(self.args['outfile'])[1]
        if ltop.check_single_gcs_file(selected_params_fn,self.args['cloud_bucket']): 
            print('selected params already exist')
        else: 
            print('Uploading selected params to GCS')
            
            #just take the file name as the GCS bucket name and upload selected params
            ltop.upload_to_bucket(os.path.split(self.args['outfile'])[1],self.args['outfile'],self.args['cloud_bucket'])
            time.sleep(self.sleep_time) 
        
        #now create an asset from the uploaded csv over in GEE
        #check if an asset exists - for the naming, :-4 is just stripping the ext
        proceed = self.check_assets_presence([self.gee_cwd+'/'+selected_params_fn[:-4]])
        if proceed: 
            print('The asset of selected params already exists')
        else:  
            print("Creating selected params asset...")
            ltop.create_gee_asset_from_gcs(selected_params_fn[:-4],f"gs://{self.args['cloud_bucket']}/{selected_params_fn}",self.gee_cwd)
            while True: 
                check_status = self.check_assets_presence([self.gee_cwd+'/'+selected_params_fn[:-4]])
                time.sleep(self.sleep_time)
                if check_status: 
                    print('The selected params have been successfully uploaded')
                    return True 
                    # break
                else: 
                    time.sleep(self.sleep_time) #TODO check time 
    
    def run_check_breakpoints(self): 
        bps_fn = 'Optimized_LT_'+str(self.args['startYear'])+'_start_'+self.args['place']+'_all_cluster_ids_tc'
        proceed = self.check_assets_presence([self.gee_cwd+'/'+bps_fn])
        #TODO might not need to keep this running the whole time, its set up like this so you can monitor if its has failed but it could take many hours to run for 
        #a big area. 
        if not proceed: 
            print('The final breakpoints do not exist, creating')
            lt_vertices_status = make_bps.generate_LTOP_breakpoints(self.args)
            while True:
                check_status = self.check_task_status(lt_vertices_status['id']) 
                time.sleep(self.sleep_time)
                if check_status == 'COMPLETED': 
                    print('The optimization process is complete, please check your final output')
                    return True 
                    # break
                elif (check_status == 'FAILED') | (check_status == 'CANCELLED'): 
                    print('The generation of the final output failed')
                    return False 
                    # break            
                else: 
                    #this time is somewhat arbitrary and should be increased for a real run
                    time.sleep(self.sleep_time)
        else: 
            print('The final output breakpoints already exist')
            return True 
        
    def runner(self): 
        """
        Master function for running the whole workflow. 
        """
        snic = self.run_check_SNIC()
        if snic: 
            kmeans = self.run_check_kmeans()
        else: 
            print('SNIC broke')
            return None
        if kmeans: 
            abs_imgs = self.run_check_abstract_images()
        else: 
            print('kmeans broke')
            return None 
        if abs_imgs: 
            spec_info = self.run_check_spectral_extraction()
        else: 
            print('abstract images broke')
            return None 
        if spec_info: 
            params = self.run_check_param_selection()
        else: 
            print('Extraction of spectral information broke')
            return None 
        if params: 
            bps = self.run_check_breakpoints()
        else: 
            print('Param selection broke')
            return None 
        if bps: 
            print('You have finished running the LTOP workflow!')
        else: 
            print('The generation of breakpoints broke')
            return None 