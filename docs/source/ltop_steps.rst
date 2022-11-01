Step-by-step guide
==================
This guide gives background for what's happening in each step throughout the workflow. Although in previous versions the 
user was required to run each step individually, the most current version executes all of these steps automatically with params defined 
at the outset by the user.   
**1 Generate SNIC image (GEE)**  

Ultimately, the optimization requires that LT be run hundreds of times to evaluate which set of parameters is best. This is not tractable for every pixel.  Further, it is not necessary:  a given set of parameters will work for pixels that have similar conditions in terms of cover and change processes.  Therefore, our first step is to find groups of pixels that have those similarities, and use them for all further steps. 
Thus, the first step is to organize our study area into patches.  We use GEE's Simple non*iterative clustering (SNIC) processing on an image that is meant to capture the spectral and temporal variability of the study area.  For SNIC to work, we need to build a single image that is a stack of single*date spectral images from several different years across the study period.  By incorporating images from across different years, we capture broad changes in land cover. 

For more information on the background, potential pitfalls etc. see the associated `Google Slides <https://docs.google.com/presentation/d/12hi10WmqZGdvJ9BjxSDukXQHGmzJNPAyJavObrmfVbg/edit?usp=sharing>`_
 
*Decisions to be made:*   

* Spectral form of images to use in stack. We use Tasseled*cap imagery because it efficiently captures spectral variance, but you could use something else. 
* Years of imagery to use in stack.  We use the beginning year, a middle year, and the end year, but you could add more or use composites.  
* The seed spacing for the SNIC algorithm.  The seeds are the spatial origin of the SNIC patches, and a tighter spacing will result in smaller patches. 

*Outputs:*   

* From this script we get a seed image, which represents the starting point of each patch. The seed image has several bands that point to mean spectral values of that seed's patch. 
* We also get a set of points that are used as input to the kmeans algorithm (next step)

**2 Kmeans cluster from SNIC patches (GEE)**   

Now we cluster the SNIC patches into similar land class categories. For more information on this process see the associated `Google Slides <https://docs.google.com/presentation/d/1nQDPUaeA5PX-_2z5P1-vAmbgDiZwgLTPdkx0mqeKHFU/edit?usp=sharing>`_

*Decisions to be made:*    

* Kmeans algorithm itself can be changed. Currently, the user can control the min and max cluster args
* The maxClusters argument could be raised or lowered 
* It is unknown how many clusters is the right number of clusters

*Outputs*   

* kmeans cluster image (02_1)
* kmeans cluster id points (FeatureCollection) (02_2)

**3 Sample Landsat Image Collections with the xx Kmeans Cluster Points (GEE) (Abstract images)**  

With the sample of Kmeans Cluster points, a point for each cluster ID, sample a time series of Landsat Imagery (B5, TCB, TCW, NBR, and NDVI). 
This sample is exported as a table from GEE and used to create abstract images. More on abstract images, how they work and why we create them in the associated `Google Slides <https://docs.google.com/presentation/d/1blIvQGvP5WWMaOtqvdfUT_trFYKiCqWr6R9214BXwHg/edit?usp=sharing>`_.   

*Decisions to be made:*    

* Can we reduce the size of the inputs (CSVs) at least by simplification?

*Outputs*    

* large CSV that contains different runs of LT

**4 Create Abstract images**  

Here we create an abstract image. We start with the table that contains a time series of spretral values for xx points. These points locations are moved to be adjacent to one aonther, and are turned into pixels with each observation in the time series a new pixel. Note that if you look at these in a GIS GUI or on GEE they will be in a weird location like in the middle of the Pacific Ocean. Don't worry about that, that is what should happen. For additional information, see the Google Slides for Abstract Images above. 

*Decisions to be made:*    

* The size of the tiff will be impacted by the number of kmeans clusters that come out of the kmeans step, changing that will change this

*Outputs*   

* One ee.Image for every year in the time series 
* shapefile with one point for each pixel location


**5 Run Abstract image for each index (GEE)**   

Runs LT for all the versions of LT on the abstract images. For more information see the associated `Google Slides <https://docs.google.com/presentation/d/1ILOG9tkkoKrtAoVAL-smhieb88SqUIkBtjrBBQbLs8w/edit?usp=sharing>`_

*Decisions to be made:*   

* Note that the indices that this is running are currently baked into the script (NDVI, NBR, TCW, TCB, B5). This is something that could be changed\

*Outputs:*    

* One csv per fitting index included in the runs (see below note on output folder)

**6 Run LT Parameter Scoring scripts (Python)**  

See Google Slides for step 8 above for more information on the paramater selection process.   

*Decisions to be made:*   

* The biggest thing here is that there are two weights for the AIC and Vertex scores that are included in this script. These weights were created based on interpreter analysis of LT runs for different areas in SE Asia. It is not yet known how well these values transfer to other parts of the world. These are set as default args and could be changed but would need to be amended in the run_ltop_complete.py script. 

*Outputs:*    

* One CSV with selected paramater information   
	
**7 Generate LTOP output in GEE**   

Generate the actual LTOP output. For more information see the associated `Google Slides <https://docs.google.com/presentation/d/1CCfXBDVSURL2VkBXm4gDNSEs3nf7-MKwu0kW30fg4yg/edit?usp=sharing>`_

*Decisions to be made:*    

* You could change the maxObvs and get a different number of bands in this output, but that functionality is not currently exposed. It could be changed if people want more control over the outputs. 

*Outputs*    

* This will generate a GEE asset which is the primary output of the LTOP process. This will be a multiband image with one band up to the max number of vertices. Defaults to 11 in the LTOP workflow.
	
**Next Steps**  

Next is the actual temporal stabilization using the output of the LTOP workflow. For more information on that process 
see the `documentation <https://github.com/eMapR/SERVIR_stabilization>`_. To look at the scripts, see the associated 
`GitHub repo <https://github.com/eMapR/SERVIR_stabilization/tree/main/scripts/GEE_scripts>`_ and for more background information see the `Google Slides <https://docs.google.com/presentation/d/1Mq0EgHAk1xWGNrel7UWlOx0mOX2trCCfbFJFxBckJe8/edit?usp=sharing>`_
