List of important scripts for running the LTOP workflow
=======================================================
As of LTOP version 0.1.0, the entire workflow runs from the GEE Python API and does not require the user to run individual steps manually. The entire workflow is now automated and just requires that the user set up certain components in advance of a run. The pertinent scripts are now available from the `GitHub repo <https://github.com/eMapR/LTOP_FTV_Py>`_. 

The important components are:

* `run_ltop_complete.py <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/run_ltop_complete.py>`_  
* `ltop.py <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/ltop.py>`_  
* `config.yml <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/config.yml>`_  
* `lt_params.py <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/lt_params.py>`_  
* `LandTrendr.py <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/LandTrendr.py>`_  

and then the five module scripts from the original workflow:    

* `SNIC <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/run_SNIC_01.py>`_  
* `kmeans 2 <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/run_kMeans_02_2.py>`_  
* `kmeans 1 <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/run_kMeans_02_1.py>`_  
* `abstract image generation <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/abstract_sampling_03.py>`_  
* `run LT for abstract images <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/abstract_imager_04.py>`_  
* `create LTOP breakpoints <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/generate_LTOP_05.py>`_  

**Note**    
The only script that user should really be concerned with is the run_ltop_complete.py and even then, 
that script defines a single class that could be called externally (see below for examples). 

All of these scripts can be either run on a local machine or in the cloud. To prepare a run the user 
should either `git clone <https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository>`_  
the full repository or if you are interested in helping with development you   
can `fork <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks>`_  
the repository to your local machine/cloud instance.  

To set up a run of the LTOP workflow, you should start with the config.yml file. This holds all of the 
important components that will be used to run the workflow. Setting all of this up in advance *should* 
ensure that your run goes smoothly. 