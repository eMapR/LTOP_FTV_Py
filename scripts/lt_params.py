#imports 
import pandas as pd	
import ee
# Initialize the library.
ee.Initialize()

def generate_lt_param_combos(segments = [6,8,10,11],spike = [0.75,0.90,1.0],recovery = [0.25,0.50,0.90,1.0],pValue = [0.05,0.10,0.15]): 
    
    '''
    Generates combinations of LandTrendr paramaters. Combinations are defined as default args and could be changed. 
    An *args or similar would have to be added to generate new/other params. 
    '''
    # list of parameter confingations
    list = []
    for seg in segments:
        for ske in spike:
            for rec in recovery:
                for pv in pValue:
                    newlist = [seg,ske,rec,pv]
                    list.append(newlist)

    # make empty list. this will parameters appended to it
    runParams = []
    counter = 1
    counter_list = []

    # iterator to asign parameters to dictionary
    for subList in list:

    # asign each parameter to template 
        # ltParamTemplate = "{timeSeries: ee.ImageCollection([]), maxSegments: "+str(subList[0])+" , spikeThreshold: "+str(subList[1])+", vertexCountOvershoot: 3, preventOneYearRecovery: true, recoveryThreshold: "+str(subList[2])+", pvalThreshold: "+str(subList[3])+", bestModelProportion: 0.75, minObservationsNeeded: "+str(subList[0])+", lt_param_id: "+str(counter)+" }"
        ltParamTemplate = {"maxSegments": subList[0], "spikeThreshold": subList[1], "vertexCountOvershoot": 3, "preventOneYearRecovery": True, "recoveryThreshold": subList[2], "pvalThreshold": subList[3], "bestModelProportion": 0.75, "minObservationsNeeded": subList[0], "param_num": counter}
    # append completed parameters dicionary to emtpy list 
        runParams.append(ltParamTemplate)
        counter_list.append(counter)
        counter += 1
    # end iterator 
    return runParams


