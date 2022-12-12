Procedures for testing LTOP processing and outputs
==================================================

LTOP is a difficult workflow/algorithm to test because unlike a classification algorithm for example, 
there is no 'reference' dataset for LTOP so knowing the outputs *a priori* is a challenge. However, 
one can inspect the individual components as you move through the workflow and then one can also look at the final 
outputs (fitted imagery, for example) to determine if the outputs make sense. In the current version (0.1.0), 
the whole workflow has been automated. Therefore, if you want to test or troubleshoot individual components you can 
use the jupyter notebook testing_run_ltop.ipynb to run individual parts of the workflow. This is a work in progress and 
will likely change and improve as the workflow becomes more polished. 

**testing_run_ltop.ipynb**

This jupyter notebook lives in the scripts directory with all the other scripts used to run LTOP. 
Unlike the fully automated version, you can run each step of the workflow sequentially and manually to 
troubleshoot or inspect specific outputs. 

**Notes** 
* The jupyter notebook is set up to import all of the modules it needs to run LTOP. Note however, that
if you are going to change things in associated modules (e.g. ltop.py) you will need to rerun the cell that imports modules. 
Otherwise, you are going to have the previous version of the module stored in memory.    
* This version is much more manual than the automated version. This means that it will not automatically upload and download csvs etc
from GEE or GCS. For example, in the 04 step where we generate one CSV for each index and the associated LandTrendr outputs on a point basis, 
the csvs need to be manually downloaded. Furthermore, there is an option here to export to Google Drive instead of GCS if people are less familar 
working with GCS. 
* In the fully automated version the code will check for you if something has been generated and if the required directories exist. In the jupyter notebook
version, this will not happen. This means that you will get an ERROR if you try to generate something in a directory that does not exist or you try to run an 
export task for something that already exists. 
* If you try to run the param selection in the jupyter notebook and you're using a lot of kmeans clusters (e.g. 2500, 5000), you may find that it will hang, especially if 
you're running in a browser. 
* A testing argument was added to the config.yml document. When set to the string 'true' this will export a Google drive output for the indices. Setting this to anything else 
will export to GCS as per the automated version. 
