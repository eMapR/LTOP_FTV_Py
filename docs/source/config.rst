What does the config.yml contain?
============================
Instead of importing the params as an executable module as was previously the case, the workflow now 
relies on importing a YAML file and running that through a function to parse the inputs into usable objects
by downstream functions. This is mostly to address potential security concerns and to facilitate runs that incorporate
multiple geometries. The YAML config file is read as a dictionary with values being checked and/or updated by the parse_params
function in the run_ltop_complete.py script. This dictionary contains all of the necessary components to run the full workflow. There are a few optional arguments that are currently (10/18/2022) set as defaults in 
various functions. See below for notes on those. 

run_times: str     
	One of either 'multiple' or 'single'. Multiple will set it up to run multiple ROIs in the same call while single assumes
	that you are going to just pass one ROI and run the workflow once. The script will error if you pass a different term than single or multiple.      
place: str   
	This will be used in naming construction throughout the process so give it a short, meaningful name. Note that if you are 
	going to run multiple geometries in a for loop this will be overwritten by the process that starts those runs.    
assetsRoot: str   
	This will be either your 'users/username' or moving to the future requirements for GEE it should be linked to a gcloud project and would look like: 'projects/name-of-your-project/assets/', for example.   
assetsChild: str  
	The folder you want your assets to end up in inside your project. Note that the script will create this folder if it does not find it in your project repo.  
version:   
	0.1.1 as of 10/18/2022 with the 0.1 designating the shift to Python.   
startYear: int  
	Most of the scripts assume 1990 is the start year. You can run it with a different time frame but generally we advise running as many years as possible in the LandTrendr algorithm.  
endYear: int  
	Most recent full year available in input imagery  
seedSpacing: int  
	This defines the starting seed spacing for the SNIC algorithm. The default is 10. See GEE documentation for more information on this param. It only needs to be changed if you are interested in the specific effects of the SNIC inputs/outputs.  
randomPts: int  
	The number of random points we use to sample the SNIC imagery. There is not a best known value but generally more is better. Default is 20,000. 
	You can try more, we don't necessarily recommend less but this depends on the area you are running. This seemed sufficient for an area the size of SE Asia.  
imageSource: str  
 One of either 'servir' or 'medoid'. The default is that anything not specified as medoid will choose servir composites. Note that as of 10/18/2022 the functionality for medoids does not currently exist.  
assetsRoot: str  
	Defined from assetsRoot variable above.  
assetsChild: str  
	Defined from assetsChild above.  
aoi: GEE FC  
	This is the study area you want to run. NOTE that it must be cast as a .geometry() object, not just a featureCollection.  
maxClusters: int  
	Defines the max clusters for the kmeans algorithm implemented in GEE. Somewhere around 5,000 seems to be the max. Generally, 2500 seems sufficient for something about the size of Cambodia.  
minClusters: int  
	Generally set to the same as maxClusters but could be set lower.  
selectedLTparams: GEE FC  
	Leave defaults and this will just be constructed for you from the other input params.   
param_scoring_inputs: str, filepath like  
	Filepath to a local directory where you want the LT outputs from running on abstract image points to reside. Note that this folder will be created for you in the script if you have not created it in advance.
	This will be dynamically updated in the code if you chose 'multiple' for the run_times arg above.   
outfile: str, filepath like  
	This should be a local directory where you want the selected LT params for generating LTOP breakpoints to end up. Note that the folder will be created for you if you have not created it in advance.  
	This will be dynamically updated in the code if you chose 'multiple' for the run_times arg above. 
njobs: int  
	Number of cores to use in param selection. This will likely be changed in future versions.    
cloud_bucket: str, GCS cloud bucket name  
	This is the name of a cloud bucket in a Google Cloud Services account. See notes in `general setup <general_setup.rst>` for setting this up. Note that the program will not do this for you, 
	you need to manually do this in advance of running or you will hit an error. 

NOTE that as of 10/18/2022, the necessary code to run medoid composites does not yet exist. When that is done, the below args will be required to generate medoid composites from existing LandTrendr modules.   
startDate: str    
A string date range formatted like '11-20' (mm-dd).     
endDate: str     
A string date range formatted like '03-10' (mm-dd).   
masked: list    
A list of things you want to mask formatted like ['cloud', 'shadow'], for example. 
  
**Other arguments**  

The class that runs LTOP takes the param dictionary as the primary input, passed as \*args, and then a sleep_time argument which can be passed separately to the class. 
This defines the time you want the program to wait before re-checking if a process or task is complete. 
There is not a 'perfect' answer here but it is mostly in place so that the program does not try to query Google's servers every iteration of a while loop.  
 