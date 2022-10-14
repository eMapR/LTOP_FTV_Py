from tabnanny import check
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
        #check if the 04 output already exists
        # this can't be done until the drive thing is resolved
        #temporary 
        proceed = input("Is the spectral information downloaded? (y/n)")
        if (proceed == 'y') | (proceed == 'yes'): 
            print('Assuming spectral extraction is done, proceeding to param selection')
        else: 
            print('Assuming spectral extraction is not done, generating now')
            lt_pt_status = run_lt_pts.run_LT_abstract_imgs(self.args)
        #for the times this is run we could check the task status but its a bit 
        #unwieldy with five tasks - ideally we just check the drive folder
        # while True: 
        #     check_status = self.check_task_status(lt_pt_status['id'])
        #     if check_status == 'COMPLETED': 
        #         print('The abstract image informatoin has been extracted and sent to Drive')
        #         break
        #     elif (check_status == 'FAILED') | (check_status == 'CANCELLED'): 
        #         print('The generation of the abstract image point information extraction has failed')
        #         break
        #     else: 
        #         #wait a bit before hitting the server again 
        #         time.sleep(10) 
        
        #this is where we would insert logic to check and download from drive 





        # #4.1 run the param selection process which happens in Python. TODO as of 10/12 this 
        # #cannot actually run without human intervention to move data down from gDrive and back up to GEE

        #put some other kind of check in here after we can upload/download correctly
        if os.path.exists(self.args['outfile']): 
            #TODO this print statement will be deprecated when the upload/download logic is correctly working
            print('The selected params already exist, please make sure they are uploaded as an asset')
        
        else: 
            print('Starting the param scoring regime')
            param_scoring.generate_selected_params(self.args) 
            #check when this thing is done
            while True: 
                check_status = os.path.exists(self.args['outfile'])
                if check_status: 
                    print('The param selection process has concluded, move to upload')
                    break
                else: 
                    #this time is somewhat arbitrary and for a full run will take some hours unless we improve this script 
                    time.sleep(30) 

        proceed = input('Have you uploaded the selected params csv to GEE? (y/n)')
        if (proceed.lower() == 'y') | (proceed =='yes'): 
            print('Assuming you have uploaded selected params, starting final output generation')
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
                    time.sleep(self.max_time)
        else: 
            #TODO this will be defunct when we change upload/download
            print('Please upload the selected params csv as an asset then try again')

# #run it- not sure if we want to run from this script or from somewhere else
# # if __name__ == '__main__': 
# #     main()
#max time is set this low just for testing 
test = RunLTOPFull(params.params,max_time = 30)
test.runner()