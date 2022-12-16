Example LTOP creation
=====================
The configuration for doing a full LTOP run varies slightly depending on what you want to do and what you're using as an AOI or collection of AOIs. 

In general, example runs can be found in the `LTOP_running_example.py script <https://github.com/eMapR/LTOP_FTV_Py/blob/main/scripts/LTOP_running_example.py>`_.
There are two basic modes the LTOP workflow can be run in, single or multiple. As of 12/16/2022 the configuration of this decision is defined in the LTOP_running_example.py 
script and requires some user input. It is done this way because there are a lot of different ways one might want to pass an aoi and because of the YAML file strucutre it is 
easier to cast the aoi to an ee object outside dealing with the YAML file. Therefore, the user can inspect the examples given in this script and decide which is the one that 
fits your needs. In the future, this could be updated to be more automated and to decide to run single or multiple based on the 'run_times' argument in the config.yml file.

With that in mind, the user needs to: 

1. change the aoi argument either in the single (default) or in the multiple runs section. If passing a single aoi it should be cast to a geometry object before passing.
If running multiple aois it should be a featureCollection whose features can be cast to geometry in the for loop shown in the multiple runs section. 
2. After dealing with the GCS setup and changing anything you want in the config.yml file double check that your run_times argument lines up with whatever you want (single or multiple)
3. You can change the 'sleep_time' keyword argument (line 32 for single) or just leave it. It defaults to 30 seconds. When LTOP is running, there are a number of steps that 
check the presence of assets or CSVs on GCS before proceeding to the next step. This just tells the program to wait sleep_time between checking for those so it does not continually query Google's servers.
4. When you run this script its going to read in the config.yml file, cast each of the arguments to its appropriate object and then start the LTOP run. 
5. Run this script from the command line or in an IDE and wait! 
6. NOTE that this can take a long time depending on how big your AOI is and how many kmeans clusters you've specified. You should run it somewhere that can remain running for the duration of the process