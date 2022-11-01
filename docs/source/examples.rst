Example LTOP creation
=====================

The LTOP workflow can be run from the run_ltop_complete.py script or it can be instantiated 
from elsewhere with the following code: 

``example = RunLTOPFull(params.params,max_time = 60)``       
``example.runner()``

where params.params is the result of import params and then referencing the dictionary inside the module. This means that one could also 
do something like:    
``from run_ltop_complete import Run LTOPFull``

For more complete examples of how to run this code see XXXXXXXXXXXXXXXXXXXXXX
This call to the RunLTOPFull class will kick of the entire LTOP workflow. The sleep_time argument is optional and has a default of 
30 seconds set in the class.