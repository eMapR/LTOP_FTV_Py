What does params.py contain?
============================
params.py gets imported as a python module in the LTOP workflow. Contained within the params.py script is a single dictionary that is accessible by the external programs that call it. This dictionary contains all of the necessary components to run the full workflow. There are a few optional arguments that are currently (10/18/2022) set as defaults in various functions. See below for notes on those. 

The first three assets are set first, they are re-used below to construct additional inputs.   
place: str   
	This will be used in naming construction throughout the process so give it a meaningful name   
assetsRoot: str   
	This will be either your 'users/username' or moving to the future requirements for GEE it should be linked to a gcloud project and would look like: 'projects  name-of-your-project/assets/', for example.   
assetsChild: str  
	The folder you want your assets to end up in inside your project. Note that the script will create this folder if it does not find it in your project repo.  

The remainder of the inputs are defined inside a dictionary called params and are callable by outside scripts by key.  
version:   
	0.1.0 as of 10/18/2022 with the 0.1 designating the shift to Python.   
place: str   
	Imported from above  
startYear: int  
	Most of the scripts assume 1990 is the start year. You can run it with a different time frame but generally we advise running as many years as possible in the LandTrendr algorithm.  
endYear: int  
	Most recent full year available in input imagery  
seedSpacing: int  
	This defines the starting seed spacing for the SNIC algorithm. The default should be 10. See GEE documentation for more information on this param. It only needs to be changed if you are interested in the specific effects of the SNIC inputs/outputs.  
randomPts: int  
	The number of random points we use to sample the SNIC imagery. There is not a best known value but generally more is better. Default should be 20,000. You can try more, we don't necessarily recommend less. This seemed sufficient for an area the size of SE Asia.  
imageSource: str  
 One of either 'servir' or 'medoid'. Note that as of 10/18/2022 the functionality for medoids does not currently exist.  
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
	This will just be constructed for you from the other input params.  
param_scoring_inputs: str, filepath like  
	Filepath to a local directory where you want the LT outputs from running on abstract image points to reside. Note that this folder will be created for you in the script if you have not created it in advance.  
outfile: str, filepath like  
	This should be a local directory where you want the selected LT params for generating LTOP breakpoints to end up. Note that the folder will be created for you if you have not created it in advance.  
njobs: int  
	Number of cores to use in param selection. This will likely be changed in future versions.  
#note that this must be set up in advance, the script will not do it for you!!  
cloud_bucket: str, GCS cloud bucket name  
	This is the name of a cloud bucket in a Google Cloud Services account. See notes below for setting this up.  

NOTE that as of 10/18/2022, the necessary code to run medoid composites does not yet exist. When that is done, the below args will be required to generate medoid composites from existing LandTrendr modules. 
"startDate":'11-20',
"endDate": '03-10',
"masked": ['cloud', 'shadow']
}
===============
Other arguments
===============

The class that runs LTOP takes the param dictionary as the primary input, passed as \*args, and then a max_time argument which can be passed separately to the class. This defines the time you want the program to wait before re-checking if a process or task is complete. There is not a 'perfect' answer here but it is mostly in place so that the program does not try to query Google's servers every half second. 