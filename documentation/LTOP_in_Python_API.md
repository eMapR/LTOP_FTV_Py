# LTOP Overview

version: 0.0.3

## These docs and the associated python scripts are currently (10/18/2022) in testing and subject to change. 

LandTrendr (LT) is a set of spectral-temporal segmentation algorithms that focuses on removing the natural spectral variations in a time series of Landsat Images. Stabilizing the natural variation in a time series emphasizes how a landscape evolves with time. This is useful in many areas as it gives information on the state of a landscape. This includes many different natural and anthropogenic processes including: growing seasons, phenology, stable landscapes, senesence, clearcut etc. LandTrendr is mostly used in Google Earth Engine (GEE), an online image processing console, where it is readily available for use.  

One impediment to running LT over large geographic domains is selecting the best paramater set for a given landscape. The LandTrendr GEE function uses 9 arguments: 8 parameters that control how spectral-temporal segmentation is executed, and an annual image collection on which to assess and remove the natural variations. The original LandTrendr article (Kennedy et al., 2010) illustrates some of the effects and sensitivity of changing some of these values. The default parameters for the LandTrendr GEE algorithm do a satisfactory job in many circumstances, but extensive testing and time is needed to hone the parameter selection to get the best segmentation out of the LandTrendr algorithm for a given region. Thus, augmenting the LandTrendr parameter selection process would save time and standardize a method to choose parameters, but we also aim to take this augmentation a step further. 

Traditionally, LT has been run over an image collection with a single LT parameter configuration and is able to remove natural variation for every pixel time series in an image. But no individual LandTrendr parameter configuration is best for all surface conditions. For example, one paramater set might be best for forest cover change while another might be preferred for agricultural phenology or reservoir flooding. To address this shortcoming, we developed a method that delineates patches of spectrally similar pixels from input imagery and then finds the best LandTrendr parameters group. We then run LandTrendr on each patch group location with a number of different paramater sets and assign scores to decide on the best parameter configuration. This process is referred to as LandTrendr Optimization (LTOP). 

## Document outline and workflow overview
This document outlines the overall workflow for running a version of LTOP that is (mostly) based on five GEE steps. Note that this version of the algorithm and the associated documentation has been updated to run in the GEE Python API and requires less input from the user than the original implementation. This is still a work in progress and will likely evolve in future versions. The way this is set up currently, you will run a Python script which will execute (almost) all of the steps in the workflow. It will generate intermediate outputs to a GEE assets directory of your choosing. Most of the steps are set up to 'wait' for the previous step to finish before initiating. 

The workflow assumes some understanding of running scripts in GEE, generating jobs and exporting assets or files to gDrive. The approach also assumes some understanding of Python and how to at least run a Python script in an IDE or from the command line. We start by outlining some of the background for the process, some information on the general overview of the workflow and how this could be set up for somebody to actually run. We then go through the steps to produce LTOP output, how the outputs can be assessed and then some of the pitfalls one might run into while carrying out this workflow. Note that to produce temporally stabilized outputs of an existing time series see the SERVIR_stabilization [GitHub repository](https://github.com/eMapR/SERVIR_stabilization). 

[General overview of theory and background](https://docs.google.com/presentation/d/1ra8y7F6_vyresNPbT3kYamVPyxWSfzAm7hCMc6w8N-M/edit?usp=sharing)

Workflow conceptual diagram: 
![img](https://docs.google.com/drawings/d/e/2PACX-1vQ9Jmb4AhD86GedXTH798O4hGCNDyCp-ZMcYEB1Ij8fuhNqc4xhDuO3x9JSttq6Tk2g9agWP2FWhoU-/pub?w=960&h=720)

Overview of script platform distribution (GEE vs Python): 
![img](https://docs.google.com/drawings/d/e/2PACX-1vTVthwPV6yUcagGQcBUSWr443lJuaeCg8r03QlmrvHOwbrp3J08lKh0zDRMORpmts3qrtkpOevzB1lm/pub?w=960&h=720)

## Background setup for running LTOP workflow 

As of LTOP version 0.1.0, the entire workflow runs from the GEE Python API and does not require the user to run individual steps manually. The entire workflow is now autmoated and just requires that the user set up certain components in advance of a run. The pertinent scripts are now available from the [GitHub repo](https://github.com/eMapR/LTOP_FTV_Py). 

The important components are: 
1. [run_ltop_complete.py](https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/run_ltop_complete.py)
2. [ltop.py](https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/ltop.py)
3. [params.py](https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/params.py)
4. [lt_params.py](https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/lt_params.py)
5. [LandTrendr.py](https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/LandTrendr.py)
and then the five module scripts from the original workflow: 
6. [SNIC](https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/run_SNIC_01.py)
7. [kmeans 1](https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/run_kMeans_02_1.py)
8. [kmeans 2](https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/run_kMeans_02_2.py)
9. [abstract image generation](https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/abstract_sampling_03.py)
10. [run LT for abstract images](https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/abstract_imager_04.py)
11. [create LTOP breakpoints](https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/generate_LTOP_05.py)

#### Note 
The only script that user should really be concerned with is the run_ltop_complete.py and even then, that script defines a single class that could be called externally (see below for examples). 

## Running the LTOP workflow 
All of these scripts can be either run on a local machine or in the cloud. To prepare a run the user should either [git clone](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository) the full repository or if you are interested in helping with development you can [fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks) the repository to your local machine/cloud instance.  

To set up a run of the LTOP workflow, you should start with the params.py file. This holds all of the important components that will be used to run the workflow. Setting all of this up in advance **should** ensure that your run goes smoothly. 

#### What does params.py contain?
params.py gets imported as a python module in the LTOP workflow. Contained within the params.py script is a single dictionary that is accessible by the external programs that call it. This dictionary contains all of the necessary components to run the full workflow. There are a few optional arguments that are currently (10/18/2022) set as defaults in various functions. See below for notes on those. 

The first three assets are set first, they are re-used below to construct additional inputs. 
place: str
	This will be used in naming construction throughout the process so give it a meaningful name 
assetsRoot: str
	This will be either your 'users/username' or moving to the future requirements for GEE it should be linked to a gcloud project and would look like: 'projects/name-of-your-project/assets/', for example.
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
	This is the study area you want to run. NOTE that it must be cast as a 
	.geometry() object, not just a featureCollection. 
maxClusters: int
	Defines the max clusters for the kmeans algorithm implemented in GEE. Somewhere around 5,000 seems to be the max. Generally, 2500 seems sufficient for something about the size of Cambodia.
minClusters: int
	Generally set to the same as maxClusters but could be set lower. 
selectedLTparams: GEE FC
	This will just be constructed for you from the other input params. 
#these should be local directories
#this one will be created automatically if it does not exist 
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

#### Other arguments
The class that runs LTOP takes the param dictionary as the primary input, passed as *args, and then a max_time argument which can be passed separately to the class. This defines the time you want the program to wait before re-checking if a process or task is complete. There is not a 'perfect' answer here but it is mostly in place so that the program does not try to query Google's servers every half second. 

#### Example run
The LTOP workflow can be run from the run_ltop_complete.py script or it can be instantiated from elsewhere with the following code: 

example = RunLTOPFull(params.params,max_time = 1200)
test.runner()

where params.params is the result of import params and then referencing the dictionary inside the module. This line of code will kick of the entire LTOP workflow. 

#### Before starting a run
Before starting, there are a few things you must do. The first and most important is to update the params.py file according to the directions laid out above. The second and crucial element is to set up the necessary components for GCS. 

Instructions for setting up GCS: 
NOTE that if you are a regular user of GCS and already have projects/buckets created you can likely skip this step or amend how the code is working to suite your needs. This is meant to be a starter for those who have not used GCS before. 
1. Create or check to see that you have a [GCS account](https://cloud.google.com/gcp?utm_source=google&utm_medium=cpc&utm_campaign=na-US-all-en-dr-bkws-all-all-trial-e-dr-1011347&utm_content=text-ad-none-any-DEV_c-CRE_622022396323-ADGP_Desk%20%7C%20BKWS%20-%20EXA%20%7C%20Txt%20~%20Google%20Cloud%20Platform%20Core-KWID_43700073027148699-kwd-6458750523&utm_term=KW_google%20cloud-ST_google%20cloud&gclid=Cj0KCQjwnbmaBhD-ARIsAGTPcfXFH3iizzepFJ4jBJwrT_T5t2HBrNZed5qcdRsU6FgZZ7oxvDTGKF8aAvjAEALw_wcB&gclsrc=aw.ds). First time users can usually get $300 in free cloud credits. 
2. Install the google-cloud-storage python module
Follow [these directions](https://cloud.google.com/sdk/docs/install) to install the google cloud sdk. 

3. Create a service account and associated key: [directions](https://cloud.google.com/resource-manager/docs/creating-managing-projects). The workflow expects a key called 'creds.json'. This should be stored in the same directory as the scripts you are running. If there is another way you want to do this some changes will have to be made in the code.

4. Create a GCS [cloud bucket](https://cloud.google.com/storage/docs/creating-buckets). Note that if you have no projects you should create a new [project](https://cloud.google.com/resource-manager/docs/creating-managing-projects) to hold the bucket. 

5. Change the params to reflect your cloud bucket name. 
 

## LTOP Work Flow theory 

### 1 Generate SNIC image (GEE)

Ultimately, the optimization requires that LT be run hundreds of times to evaluate which set of parameters is best. This is not tractable for every pixel.  Further, it is not necessary:  a given set of parameters will work for pixels that have similar conditions in terms of cover and change processes.  Therefore, our first step is to find groups of pixels that have those similarities, and use them for all further steps. 

Thus, the first step is to organize our study area into patches.  We use GEE's Simple non-iterative clustering (SNIC) processing on an image that is meant to capture the spectral and temporal variability of the study area.  For SNIC to work, we need to build a single image that is a stack of single-date spectral images from several different years across the study period.  By incorporating images from across different years, we capture broad changes in land cover. 

For more information on the background, potential pitfalls etc. see the associated [Google Slides](https://docs.google.com/presentation/d/12hi10WmqZGdvJ9BjxSDukXQHGmzJNPAyJavObrmfVbg/edit?usp=sharing)
 
#### Decisions to be made:
- Spectral form of images to use in stack. We use Tasseled-cap imagery because it efficiently captures spectral variance, but you could use something else. 
- Years of imagery to use in stack.  We use the beginning year, a middle year, and the end year, but you could add more or use composites.  
- The seed spacing for the SNIC algorithm.  The seeds are the spatial origin of the SNIC patches, and a tighter spacing will result in smaller patches. 

#### Outputs:
- From this script we get a seed image, which represents the starting point of each patch. The seed image has several bands that point to mean spectral values of that seed's patch. 
- We also get a set of points that are used as input to the kmeans algorithm (next step)

### 2 Kmeans cluster from SNIC patches (GEE) 

Now we cluster the SNIC patches into similar land class categories. For more information on this process see the associated [Google Slides](https://docs.google.com/presentation/d/1nQDPUaeA5PX-_2z5P1-vAmbgDiZwgLTPdkx0mqeKHFU/edit?usp=sharing)

#### Decisions to be made: 
- Kmeans algorithm itself can be changed. Currently, the user can control the min and max cluster args
- The maxClusters argument could be raised or lowered 
- It is unknown how many clusters is the right number of clusters

#### Outputs
- kmeans cluster image (02_1)
- kmeans cluster id points (FeatureCollection) (02_2)

### 3 Sample Landsat Image Collections with the xx Kmeans Cluster Points (GEE) (Abstract images)

With the sample of Kmeans Cluster points, a point for each cluster ID, sample a time series of Landsat Imagery (B5, TCB, TCW, NBR, and NDVI). This sample is exported as a table from GEE and used to create abstract images. More on abstract images, how they work and why we create them in the associated [Google Slides](https://docs.google.com/presentation/d/1blIvQGvP5WWMaOtqvdfUT_trFYKiCqWr6R9214BXwHg/edit?usp=sharing).   

#### Decisions to be made: 
- Can we reduce the size of the inputs (CSVs) at least by simplification?

#### Outputs
- large CSV that contains different runs of LT

### 4 Create Abstract images

Here we create an abstract image. We start with the table that contains a time series of spretral values for xx points. These points locations are moved to be adjacent to one aonther, and are turned into pixels with each observation in the time series a new pixel. Note that if you look at these in a GIS GUI or on GEE they will be in a weird location like in the middle of the Pacific Ocean. Don't worry about that, that is what should happen. For additional information, see the Google Slides for Abstract Images above. 

#### Decisions to be made: 
- The size of the tiff will be impacted by the number of kmeans clusters that come out of the kmeans step, changing that will change this

#### Outputs
- One ee.Image for every year in the time series 
- shapefile with one point for each pixel location


### 5 Run Abstract image for each index (GEE). 

Runs LT for all the versions of LT on the abstract images. For more information see the associated [Google Slides](https://docs.google.com/presentation/d/1ILOG9tkkoKrtAoVAL-smhieb88SqUIkBtjrBBQbLs8w/edit?usp=sharing)

#### Decisions to be made: 
- Note that the indices that this is running are currently baked into the script (NDVI, NBR, TCW, TCB, B5). This is something that could be changed\

#### Outputs: 
- One csv per fitting index included in the runs (see below note on output folder)

### 6 Run LT Parameter Scoring scripts (Python). 

See Google Slides for step 8 above for more information on the paramater selection process. 

#### Decisions to be made: 
- The biggest thing here is that there are two weights for the AIC and Vertex scores that are included in this script. These weights were created based on interpreter analysis of LT runs for different areas in SE Asia. It is not yet known how well these values transfer to other parts of the world. These are set as default args and could be changed but would need to be amended in the run_ltop_complete.py script. 

#### Outputs: 
- One CSV with selected paramater information 
	
### 7 Generate LTOP output in GEE. 

Generate the actual LTOP output. For more information see the associated [Google Slides](https://docs.google.com/presentation/d/1CCfXBDVSURL2VkBXm4gDNSEs3nf7-MKwu0kW30fg4yg/edit?usp=sharing)

#### Decisions to be made: 
- You could change the maxObvs and get a different number of bands in this output, but that functionality is not currently exposed. It could be changed if people want more control over the outputs. 

#### Outputs
- This will generate a GEE asset which is the primary output of the LTOP process. This will be a multiband image with one band up to the max number of vertices. Defaults to 11 in the LTOP workflow.
	
### Next Steps

Next is the actual temporal stabilization using the output of the LTOP workflow. For more information on that process see the [documentation](https://github.com/eMapR/SERVIR_stabilization). To look at the scripts, see the associated    [GitHub repo](https://github.com/eMapR/SERVIR_stabilization/tree/main/scripts/GEE_scripts) and for more background information see the [Google Slides](https://docs.google.com/presentation/d/1Mq0EgHAk1xWGNrel7UWlOx0mOX2trCCfbFJFxBckJe8/edit?usp=sharing)
