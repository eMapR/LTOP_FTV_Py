from multiprocessing import Value
import ee
import math
ee.Initialize()

# #######################################################################################
# ###### INDEX CALCULATION FUNCTIONS ####################################################
# #######################################################################################

# TASSELLED CAP
def tcTransform(img): 
    b = ee.Image(img).select(["B1", "B2", "B3", "B4", "B5", "B7"]) # select the image bands
    brt_coeffs = ee.Image.constant([0.2043, 0.4158, 0.5524, 0.5741, 0.3124, 0.2303]) # set brt coeffs - make an image object from a list of values - each of list element represents a band
    grn_coeffs = ee.Image.constant([-0.1603, -0.2819, -0.4934, 0.7940, -0.0002, -0.1446]) # set grn coeffs - make an image object from a list of values - each of list element represents a band
    wet_coeffs = ee.Image.constant([0.0315, 0.2021, 0.3102, 0.1594, -0.6806, -0.6109]) # set wet coeffs - make an image object from a list of values - each of list element represents a band

    sum = ee.Reducer.sum() # create a sum reducer to be applyed in the next steps of summing the TC-coef-weighted bands
    brightness = b.multiply(brt_coeffs).reduce(sum) # multiply the image bands by the brt coef and then sum the bands
    greenness = b.multiply(grn_coeffs).reduce(sum) # multiply the image bands by the grn coef and then sum the bands
    wetness = b.multiply(wet_coeffs).reduce(sum) # multiply the image bands by the wet coef and then sum the bands
    angle = (greenness.divide(brightness)).atan().multiply(180/math.pi).multiply(100)
    tc = (brightness.addBands(greenness)
                    .addBands(wetness)
                    .addBands(angle)
                    .select([0,1,2,3], ['TCB','TCG','TCW','TCA']) #stack TCG and TCW behind TCB with .addBands, use select() to name the bands
                    .set('system:time_start', img.get('system:time_start')))
    return tc


# NBR
def nbrTransform(img): 
  nbr = (img.normalizedDifference(['B4', 'B7']) # calculate normalized difference of B4 and B7. orig was flipped: ['B7', 'B4']
              .multiply(1000) # scale results by 1000
              .select([0], ['NBR']) # name the band
              .set('system:time_start', img.get('system:time_start'))
              )
  return nbr

#TODO there is nothing wrong here, it just hasn't been translated yet because it wasn't immediately needed 
# #Ben added
# # NDFI - from CODED utility (original: users/bullocke/coded:coded/miscUtilities)
#  ndfiTransform = function(img) {

#   # pre-defined endmembers
#    params = ee.Dictionary({
#     'cfThreshold': 0.01, # CLOUD THRESHOLD 
#     'soil': [2000, 3000, 3400, 5800, 6000, 5800],
#     'gv': [500, 900, 400, 6100, 3000, 1000],
#     'npv': [1400, 1700, 2200, 3000, 5500, 3000],
#     'shade': [0, 0, 0, 0, 0, 0],
#     'cloud': [9000, 9600, 8000, 7800, 7200, 6500]
#     })
    
#     /* Utility function for calculating spectral indices */
#      gv = params.get('gv')
#      shade = params.get('shade')
#      npv = params.get('npv')
#      soil = params.get('soil')
#      cloud = params.get('cloud')
#     # cfThreshold = ee.Image.constant(params.get('cfThreshold'))
#     /*  Do spectral unmixing on a single image  */
#      unmixImage = ee.Image(img).unmix([gv, shade, npv, soil, cloud], true,true)
#                     .rename(['band_0', 'band_1', 'band_2','band_3','band_4'])
#      newImage = ee.Image(img).addBands(unmixImage)
#     # mask = newImage.select('band_4').lt(cfThreshold)
  
#      ndfi = unmixImage.expression(
#       '((GV / (1 - SHADE)) - (NPV + SOIL)) / ((GV / (1 - SHADE)) + NPV + SOIL)', {
#         'GV': unmixImage.select('band_0'),
#         'SHADE': unmixImage.select('band_1'),
#         'NPV': unmixImage.select('band_2'),
#         'SOIL': unmixImage.select('band_3')
#       }) 
#      ndvi = ee.Image(img).normalizedDifference(['B4','B3']).rename('NDVI')
#      evi = ee.Image(img).expression(
#           'float(2.5*(((B4/10000) - (B3/10000)) / ((B4/10000) + (6 * (B3/10000)) - (7.5 * (B1/10000)) + 1)))',
#           {
#               'B4': ee.Image(img).select(['B4']),
#               'B3': ee.Image(img).select(['B3']),
#               'B1': ee.Image(img).select(['B1'])
#           }).rename('EVI')    
          
#      toExp = newImage
#           .addBands([ndfi.rename(['NDFI']), ndvi, evi])
#           .select(['band_0','band_1','band_2','band_3','NDFI','NDVI','EVI','B1','B2','B3','B4','B5'])
#           .rename(['GV','Shade','NPV','Soil','NDFI','NDVI','EVI','Blue','Green','Red','NIR','SWIR1']) 
#           #.updateMask(mask)

#   toExp = toExp.select(['NDFI'])
#               .multiply(1000)
#               .set('system:time_start', img.get('system:time_start'))
#   return toExp

# }

# NDVI
def ndviTransform(img): 
  ndvi = (img.normalizedDifference(['B4', 'B3']) # calculate normalized dif between band 4 and band 3 (B4-B3/B4_B3)
              .multiply(1000) # scale results by 1000
              .select([0], ['NDVI']) # name the band
              .set('system:time_start', img.get('system:time_start'))
              )
  return ndvi

                
# # NDSI
#  ndsiTransform = function(img){ 
#    ndsi = img.normalizedDifference(['B2', 'B5']) # calculate normalized dif between band 4 and band 3 (B4-B3/B4_B3)
#                 .multiply(1000) # scale results by 1000
#                 .select([0], ['NDSI']) # name the band
#                 .set('system:time_start', img.get('system:time_start'))
#   return ndsi
# }

# # NDMI
#  ndmiTransform = function(img) {
#      ndmi = img.normalizedDifference(['B4', 'B5']) # calculate normalized difference of B4 and B7. orig was flipped: ['B7', 'B4']
#                  .multiply(1000) # scale results by 1000
#                  .select([0], ['NDMI']) # name the band
#                  .set('system:time_start', img.get('system:time_start'))
#     return ndmi
# }

# # EVI
#  eviTransform = function(img) {
#    evi = img.expression(
#       '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
#         'NIR': img.select('B4'),
#         'RED': img.select('B3'),
#         'BLUE': img.select('B1')
#   })
#   .multiply(1000) # scale results by 1000
#   .select([0], ['EVI']) # name the band
#   .set('system:time_start', img.get('system:time_start')) 
#   return evi
# }

# CALCULATE A GIVEN INDEX
def calcIndex(img, inx, flip): 
    # make sure index string in upper case
    inx = inx.upper()
    
    # figure out if we need to calc tc
    tcList = ['TCB', 'TCG', 'TCW', 'TCA']
    
    #TODO this threw a ValueError on 'NBR' is not in the list - this seems likes its just an issue with indexing
    #that worked in GEE but doesn't work in Python. If that's not the case, we're bypassing a legit error
    try: 
      doTC = tcList.index(inx)
      if doTC >= 0: 
          tc = tcTransform(img)
    except ValueError: 
      pass  
    # need to flip some indices if this is intended for segmentation
    indexFlip = 1
    if flip == 1: 
        indexFlip = -1
  
    # need to cast raw bands to float to make sure that we don't get errors regarding incompatible bands
    # ...derivations are already float because of division or multiplying by decimal
    #note that this was a switch/case/default syntax but that only works in python 3.10
    #its possible there are some issues with other packages when running that version so for compatibility its changed to if/elif but 
    #that might not be the best way to do it. 
    indexImg = 0 
    if inx == 'B1': 
      indexImg = img.select(['B1']).float()#.multiply(indexFlip)
    elif inx == 'B2':
      indexImg = img.select(['B2']).float()#.multiply(indexFlip)
    elif inx == 'B3':
      indexImg = img.select(['B3']).float()#.multiply(indexFlip)
    elif inx == 'B4':
      indexImg = img.select(['B4']).multiply(indexFlip).float()
    elif inx == 'B5':
      indexImg = img.select(['B5']).float()#.multiply(indexFlip)
    elif inx == 'B7':
      indexImg = img.select(['B7']).float()#.multiply(indexFlip)
    #TODO note that these modules just haven't been translated yet 
    elif inx == 'NBR':
      indexImg = nbrTransform(img).multiply(indexFlip)
    # elif inx == 'NDMI':
    #   indexImg = ndmiTransform(img).multiply(indexFlip)
    #   break
    elif inx == 'NDVI':
      indexImg = ndviTransform(img).multiply(indexFlip)
    # case 'NDSI':
    #   indexImg = ndsiTransform(img).multiply(indexFlip)
    #   break
    # case 'EVI':
    #   indexImg = eviTransform(img).multiply(indexFlip)
    #   break
    elif inx == 'TCB':
      indexImg = tc.select(['TCB'])#.multiply(indexFlip)
    elif inx == 'TCG':
      indexImg = tc.select(['TCG']).multiply(indexFlip)
    elif inx == 'TCW':
      indexImg = tc.select(['TCW']).multiply(indexFlip)
    elif inx == 'TCA':
      indexImg = tc.select(['TCA']).multiply(indexFlip)
    #  case 'NDFI':
    #   indexImg = ndfiTransform(img).multiply(indexFlip)
    #   break
    # default:
    else: 
      print('The index you provided is not supported')

    return indexImg.set('system:time_start', img.get('system:time_start'))

def calc_bands(img,bandList): 
    allStack = calcIndex(img, bandList[0], 0)
    for band in range(1,len(bandList)): 
        bandImg = calcIndex(img, bandList[band], 0)
        allStack = allStack.addBands(bandImg)
    return allStack.set('system:time_start', img.get('system:time_start'))

def transformSRcollection(srCollection, bandList): 
    return srCollection.map(lambda x: calc_bands(x,bandList))
####################################################################################
#INDEX FLIPPER
def indexFlipper(index):
  indexObj = {
    'NBR': -1,
    'NDVI': -1,
    'NDSI': -1,  # ???? this is a tricky one
    'NDMI': -1,
    'EVI': -1,  
    'TCB': 1,
    'TCG': -1,
    'TCW': -1,
    'TCA': -1,
    'B1': 1,
    'B2': 1,
    'B3': 1,
    'B4': -1,
    'B5': 1,
    'B7': 1,
    'ENC': 1,
    'ENC1': 1,
    'TCC': 1,  
    'NBRz': 1,
    'B5z': 1
  }
  return indexObj[index]
####################################################################################

#code to build LT collection with calculated indices 
# STANDARDIZE A INDEX INDEX - all disturbances are up
def standardize_helper1(img,mean): 
  return img.subtract(mean).set('system:time_start', img.get('system:time_start'))

def standardize_helper2(img,stdDev): 
  return img.divide(stdDev).set('system:time_start', img.get('system:time_start'))

def standardize(collection): 
  mean = collection.reduce(ee.Reducer.mean())
  stdDev = collection.reduce(ee.Reducer.stdDev())

  meanAdj = collection.map(lambda img: standardize_helper1(img,mean))

  return meanAdj.map(lambda img: standardize_helper2(img,stdDev))
# STANDARDIZE TASSELED CAP BRIGHTNESS GREENNESS WETNESS AND REDUCE THE COLLECTION
def makeTCcomp_helper1(img): 
  tcb = calcIndex(img, 'TCB', 1)#.unmask(0)
  tcg = calcIndex(img, 'TCG', 1)#.unmask(0)
  tcw = calcIndex(img, 'TCW', 1)#.unmask(0)
  return (tcb.addBands(tcg)
            .addBands(tcw)
            .set('system:time_start', img.get('system:time_start')))

def makeTCcomp_helper2(img,reducer): 
  imgCollection = ee.ImageCollection.fromImages(
      [
        img.select(['TCB'],['Z']),
        img.select(['TCG'],['Z']),
        img.select(['TCW'],['Z'])
      ]
    )
  reducedImg = 0 
  if reducer == 'mean': 
    reducedImg = imgCollection.mean()
  elif reducer == 'max':
    reducedImg = imgCollection.max()
  elif reducer == 'sum':
    reducedImg = imgCollection.sum()
  else: 
      print('The reducer you provided is not supported')
  
  return reducedImg.multiply(1000).set('system:time_start', img.get('system:time_start'))            

def makeTCcomposite(annualSRcollection, reducer): 
  TCcomposite = annualSRcollection.map(makeTCcomp_helper1)

  tcb = TCcomposite.select(['TCB'])
  tcg = TCcomposite.select(['TCG'])
  tcw = TCcomposite.select(['TCW'])
  
  # standardize the TC bands
  tcbStandard = standardize(tcb)
  tcgStandard = standardize(tcg)
  tcwStandard = standardize(tcw)

# combine the standardized TC band collections into a single collection - TODO combine might throw an error, perhaps it should be merge?
  tcStandard = tcbStandard.combine(tcgStandard).combine(tcwStandard)

  TCcomposite = tcStandard.map(lambda img: makeTCcomp_helper2(img,reducer))
  return TCcomposite

# STANDARDIZE B5, TCB, TCG, NBR AND REDUCE THE COLLECTION
def makeEnsComps_helper1(img): 
  b5   = calcIndex(img, 'B5', 1)
  b7   = calcIndex(img, 'B7', 1)
  tcw  = calcIndex(img, 'TCW', 1)
  tca  = calcIndex(img, 'TCA', 1)
  ndmi = calcIndex(img, 'NDMI', 1)
  nbr  = calcIndex(img, 'NBR', 1)
  return (b5.addBands(b7)
            .addBands(tcw)
            .addBands(tca)
            .addBands(ndmi)
            .addBands(nbr)
            .set('system:time_start', img.get('system:time_start')))

def makeEnsComps_helper2(img,reducer): 
  imgCollection = ee.ImageCollection.fromImages(
    [
      img.select(['B5'],['Z']),
      img.select(['B7'],['Z']),
      img.select(['TCW'],['Z']),
      img.select(['TCA'],['Z']),
      img.select(['NDMI'],['Z']),
      img.select(['NBR'],['Z']),
    ]
  )
  reducedImg = 0 
  if reducer == 'mean':
    reducedImg = imgCollection.mean()
  elif reducer == 'max':
    reducedImg = imgCollection.max()
  elif reducer == 'sum':
    reducedImg = imgCollection.sum()
  else:
    print('The reducer you provided is not supported')
  return reducedImg.multiply(1000).set('system:time_start', img.get('system:time_start'))            

def makeEnsemblecomposite(annualSRcollection, reducer): 
  # make a collection of the ensemble indices stacked as bands
  stack = annualSRcollection.map(makeEnsComps_helper1)

  # make subset collections of each index
  b5 = stack.select('B5')
  b7 = stack.select('B7')
  tcw = stack.select('TCW')
  tca = stack.select('TCA')
  ndmi = stack.select('NDMI')
  nbr = stack.select('NBR')
  
# standardize each index to mean 0 stdev 1
  b5Standard = standardize(b5)
  b7Standard = standardize(b7)
  tcwStandard = standardize(tcw)
  tcaStandard = standardize(tca)
  ndmiStandard = standardize(ndmi)
  nbrStandard = standardize(nbr)
  
# combine the standardized band collections into a single collection
  standard = (b5Standard.combine(b7Standard)
                        .combine(tcwStandard)
                        .combine(tcaStandard)
                        .combine(ndmiStandard)
                        .combine(nbrStandard))

  # reduce the collection to a single value
  composite = standard.map(lambda img: makeEnsComps_helper2(img,reducer))
  
  return composite

def makeEnsComps1_helper1(img): 
  b5   = calcIndex(img, 'B5', 1)
  tcb  = calcIndex(img, 'TCB', 1)
  tcg  = calcIndex(img, 'TCG', 1)
  nbr  = calcIndex(img, 'NBR', 1)
  return (b5.addBands(tcb)
            .addBands(tcg)
            .addBands(nbr)
            .set('system:time_start', img.get('system:time_start')))

def makeEnsComps1_helper2(img,reducer): 
  imgCollection = ee.ImageCollection.fromImages(
      [
        img.select(['B5'],['Z']),#.pow(ee.Image(1)).multiply(img.select('B5').gte(0).where(img.select('B5').lt(0),-1)),
        img.select(['TCB'],['Z']),#.pow(ee.Image(1.5)).multiply(img.select('TCB').gte(0).where(img.select('TCB').lt(0),-1)),
        img.select(['TCG'],['Z']),#.pow(ee.Image(1.5)).multiply(img.select('TCG').gte(0).where(img.select('TCG').lt(0),-1)),
        img.select(['NBR'],['Z'])#.pow(ee.Image(1.5)).multiply(img.select('NBR').gte(0).where(img.select('NBR').lt(0),-1))
      ]
    )
  reducedImg = 0 
  if reducer == 'mean':
    reducedImg = imgCollection.mean()
    
  elif reducer == 'max':
    reducedImg = imgCollection.max()
    
  elif reducer == 'sum':
    reducedImg = imgCollection.sum()
  else: 
      print('The reducer you provided is not supported')
  return reducedImg.multiply(1000).set('system:time_start', img.get('system:time_start'))            

# STANDARDIZE B5, TCB, TCG, NBR AND REDUCE THE COLLECTION
def makeEnsemblecomposite1(annualSRcollection, reducer): 
  # make a collection of the ensemble indices stacked as bands
  TCcomposite = annualSRcollection.map(makeEnsComps1_helper1)
    
  # make subset collections of each index
  b5 = TCcomposite.select('B5')
  tcb = TCcomposite.select('TCB')
  tcg = TCcomposite.select('TCG')
  nbr = TCcomposite.select('NBR')
  
  # standardize each index - get z-score
  b5Standard = standardize(b5)
  tcbStandard = standardize(tcb)
  tcgStandard = standardize(tcg)
  nbrStandard = standardize(nbr)
  
  # combine the standardized TC band collections into a single collection
  tcStandard = b5Standard.combine(tcbStandard).combine(tcgStandard).combine(nbrStandard)

  # reduce the collection to a single value
  TCcomposite = tcStandard.map(lambda img: makeEnsComps1_helper2(img,reducer))
    
  return TCcomposite


def zFunc_helper1(img,index): 
  return calcIndex(img,index,1)

def zFunc_helper2(img): 
  return img.multiply(1000).set('system:time_start', img.get('system:time_start')) 

def standardizeIndex(collection, index): 
  
  zCollection = collection.map(lambda img: zFunc_helper1(img,index))

  zCollection = standardize(zCollection)

  zCollection = zCollection.map(zFunc_helper2)

  return zCollection

def buildLT_helper1(img,index,ftvList): 
  allStack = calcIndex(img, index, 1)
  ftvimg = 0 
  for i in range(len(ftvList)): 
    ftvimg = calcIndex(img, ftvList[i], 0).select([ftvList[i]],['ftv_'+ftvList[i].lower()])
    allStack = allStack.addBands(ftvimg).set('system:time_start', img.get('system:time_start'))
  return allStack

# BUILD AN LT COLLECTION
def buildLTcollection(collection, index, ftvList): 
#print(ftvList)
  LTcollection = 0 
# switch(index){
  # tasseled cap composite
  if index == 'TCC':
    LTcollection = makeTCcomposite(collection, 'mean') 
  elif index == 'TCM':
    LTcollection = makeTCcomposite(collection, 'max') 
  elif index == 'TCS':
    LTcollection = makeTCcomposite(collection, 'sum') 
  
  # 6-band composite - Based on Figure 3 of the linked paper: https:#larse.forestry.oregonstate.edu/sites/larse/files/pub_pdfs/Cohen_et_al_2018.pdf
  elif index == 'ENC':
    LTcollection = makeEnsemblecomposite(collection, 'mean') 
  elif index == 'ENM':
    LTcollection = makeEnsemblecomposite(collection, 'max') 
  elif index == 'ENS':
    LTcollection = makeEnsemblecomposite(collection, 'sum') 
  
  # 6-band composite - Based on Table 5 of the linked paper: https:#larse.forestry.oregonstate.edu/sites/larse/files/pub_pdfs/Cohen_et_al_2018.pdf
  elif index == 'ENC1':
    LTcollection = makeEnsemblecomposite1(collection, 'mean') 
  elif index == 'ENM1':
    LTcollection = makeEnsemblecomposite1(collection, 'max') 
  elif index == 'ENS1':
    LTcollection = makeEnsemblecomposite1(collection, 'sum') 
  
  # standardized versions of indices: mean 0 stdDev 1  
  elif index == 'B5z':
    LTcollection = standardizeIndex(collection, 'B5') 
  elif index == 'B7z':
    LTcollection = standardizeIndex(collection, 'B7') 
  elif index == 'TCWz':
    LTcollection = standardizeIndex(collection, 'TCW') 
  elif index == 'TCAz':
    LTcollection = standardizeIndex(collection, 'TCA') 
  elif index == 'NDMIz':
    LTcollection = standardizeIndex(collection, 'NDMI') 
  elif index == 'NBRz':
    LTcollection = standardizeIndex(collection, 'NBR') 
  else: 
    LTcollection = collection.map(lambda img: buildLT_helper1(img,index,ftvList))
              
  return LTcollection

#########################################################################################################
###### UNPACKING LT-GEE OUTPUT STRUCTURE FUNCTIONS ##### 
#########################################################################################################

# ----- FUNCTION TO EXTRACT VERTICES FROM LT RESULTS AND STACK BANDS -----
def getLTvertStack(lt, runParams): 
  lt = lt.select('LandTrendr')
  emptyArray = []                              # make empty array to hold another array whose length will vary depending on maxSegments parameter    
  vertLabels = []                              # make empty array to hold band names whose length will vary depending on maxSegments parameter 
  for i in range(0,runParams['maxSegments']+1):  # loop through the maximum number of vertices in segmentation and fill empty arrays                        # define vertex number as string 
    vertLabels.append("vert_"+str(i))               # make a band name for given vertex
    emptyArray.append(0)                             # fill in emptyArray
  zeros = ee.Image(ee.Array([emptyArray,        # make an image to fill holes in result 'LandTrendr' array where vertices found is not equal to maxSegments parameter plus 1
                            emptyArray,
                            emptyArray]))
  
  lbls = [['yrs_','src_','fit_'], vertLabels,] # labels for 2 dimensions of the array that will be cast to each other in the final step of creating the vertice output 

  vmask = lt.arraySlice(0,3,4)           # slices out the 4th row of a 4 row x N col (N = number of years in annual stack) matrix, which identifies vertices - contains only 0s and 1s, where 1 is a vertex (referring to spectral-temporal segmentation) year and 0 is not
  
  ltVertStack = (lt.arrayMask(vmask)       # uses the sliced out isVert row as a mask to only include vertice in this data - after this a pixel will only contain as many "bands" are there are vertices for that pixel - min of 2 to max of 7. 
                    .arraySlice(0, 0, 3)          # ...from the vertOnly data subset slice out the vert year row, raw spectral row, and fitted spectral row
                    .addBands(zeros)              # ...adds the 3 row x 7 col 'zeros' matrix as a band to the vertOnly array - this is an intermediate step to the goal of filling in the vertOnly data so that there are 7 vertice slots represented in the data - right now there is a mix of lengths from 2 to 7
                    .toArray(1)                   # ...concatenates the 3 row x 7 col 'zeros' matrix band to the vertOnly data so that there are at least 7 vertice slots represented - in most cases there are now > 7 slots filled but those will be truncated in the next step
                    .arraySlice(1, 0, runParams['maxSegments']+1) # ...before this line runs the array has 3 rows and between 9 and 14 cols depending on how many vertices were found during segmentation for a given pixel. this step truncates the cols at 7 (the max verts allowed) so we are left with a 3 row X 7 col array
                    .arrayFlatten(lbls, ''))      # ...this takes the 2-d array and makes it 1-d by stacking the unique sets of rows and cols into bands. there will be 7 bands (vertices) for vertYear, followed by 7 bands (vertices) for rawVert, followed by 7 bands (vertices) for fittedVert, according to the 'lbls' list

  return ltVertStack                               # return the stack


