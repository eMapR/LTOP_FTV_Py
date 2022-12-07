import os
import ast
import pandas as pd
import numpy as np
import glob
import json
from sklearn.metrics import mean_squared_error
from math import sqrt
import math
import sys
from multiprocessing import Pool


"""
**************************************
* arr_to_col
*
*
*
*
***************************************
"""
def arr_to_col(df,startYear,endYear):
	# make vert list from start and end year
	vertyearlist = []
	
	for year in range(startYear,endYear+1):
	
		vertyearlist.append("vert"+str(year)[-2:])

	df[vertyearlist]=pd.DataFrame(df.vert.tolist(), index= df.index)

	return 1 
"""
**************************************
*
*
*
*
***************************************
"""
def dfprep(df,startYear,endYear):

	# add LT parameter config column
	df['paramNum'] = 0

	# make vert list from start and end year
	vertyearlist = []
	for year in range(startYear,endYear+1):
		vertyearlist.append("vert"+str(year)[-2:])

	# adds vertices year columns
	df[vertyearlist]=0

	# adds a column for normalized rmse
	df['NRMSE'] = 0.0

	# adds AIC score column
	df['AIC'] =0.0

	# adds AICc column
	df['AICc'] =0.0

	# sort dataframe by values for columns
	dfsorted = df.sort_values(by=['cluster_id','params'],ignore_index=True)

	# add an index id for the sort dataframe 
	dfsorted['index_cid'] = dfsorted.index+1 

	# makes a list of number for the range of landtrendr parameters used  <<<<<<<<<<<<<<<<<<<<< Not sure if this needs to automated 
	listvalues = list(range(1,144+1)) #add what 144 is 
		
	# make a list of of repeating param values for each configuration
	ser = listvalues * int(len(dfsorted)/len(listvalues))
	
	dfsorted['paramNum']= ser + listvalues[:len(dfsorted)-len(ser)]
	
	return dfsorted      


"""
**************************************
*
*
*
*
***************************************
"""

def read_csv(filename,startYear=1990,endYear=2021):
	"""
	wrap your csv importer in a function that can be mapped
	"""
	#converts a filename to a pandas dataframe
	
	# works for linux - TODO I don't think this is needed???
	#dftmp = pd.read_csv(filename, converters={'fitted':eval, 'orig': eval, 'vert': eval, 'year': eval})
	# this works for windows
	dftmp = pd.read_csv(filename)

	dftmp2 = dfprep(dftmp,startYear,endYear)
	
	return dftmp2

def read_in_CSVs(csv_dir,njobs):

	# get a list of file names
	if csv_dir.endswith('/'): 
		files = glob.glob(csv_dir+"*.csv")
	else: 
		files = glob.glob(csv_dir+'/'+"*.csv")	

	print('The files we are going to process are', files)

	# set up your pool
	with Pool(processes=njobs) as pool: # or whatever your hardware can support
	# have your pool map the file names to dataframes
		df_list = pool.map(read_csv, files)

	return df_list

def midpoint(lis):
	"""
	TODO Not sure what this is supposed to do 
	"""
	if 99999 in lis:
		ind = lis.index(99999)
		m = (lis[ind-1]+lis[ind+1])/2
		lis[ind] = m
		return lis
	else:
		return lis

def summed_across_vertices(df_numOfPoints, startYear=1990, endYear=2021):
	"""
	this is doing some kind of complicated data cleaning 
	"""
	# remove any row with no data
	dftmp = df_numOfPoints.dropna()

	# makes a list  [1990,1991 ...,2019 , 2020] a template of all the years in the time series.
	goodYear = list(range(startYear,endYear+1))

	# empty List for temporary placment of a single points summed vert array ?
	vertStrings = []
		
	dftmp["vert"] = dftmp["vert"].str[1:-1].apply(ast.literal_eval)
	dftmp["year"] = dftmp["year"].str[1:-1].apply(ast.literal_eval)
	dftmp["fitted"] = dftmp["fitted"].str[1:-1].apply(ast.literal_eval)
	dftmp["orig"] = dftmp["orig"].str[1:-1].apply(ast.literal_eval)
	
	# make column for the len of lt data arrays. 
	for index, row in dftmp.iterrows():
		# extracts a single list for the list of list  
		objVert = row['vert'] #[int(i) for i in json.loads(vert)[0]]  # example output [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1]
		objYear = row['year'] # example output [1990, 1991, 1992, 1993, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2$

		# finds the missing year if there is one in the above  Year list 
		yearCheck = [ele for ele in range(startYear, endYear+1) if ele not in objYear]

		# check for missing elements in lists and add 0 if element is missing
		for place in yearCheck:

			mis = goodYear.index(place)
			objVert.insert(mis,0)
			objYear.insert(mis,place)

		# add value to miss fitted and orig midpoint calc
		# objFit = midpoint(objFit)		
		# objOrig = midpoint(objOrig)
		# #vertStrings.append(objVert)
		dftmp.at[index, 'vert'] = objVert
		dftmp.at[index, 'year'] = objYear
		# dftmp.at[index, 'fitted'] = objFit
		# dftmp.at[index, 'orig'] = objOrig
		
	dftmp['len_vert'] = dftmp['vert'].str.len()
	dftmp['len_year'] = dftmp['year'].str.len()
	dftmp['len_fitted'] = dftmp['fitted'].str.len()
	dftmp['len_orig'] = dftmp['orig'].str.len()
		
	return dftmp


"""
**************************************
*
*
*
*
***************************************
"""
#def pool_summed_vert(df_list_cluster_id,start,end):
def pool_summed_vert(df_list_cluster_id,startYear,endYear,njobs):

	# set up pool works on linux
	with Pool(processes=njobs) as pool: # or whatever your hardware can support
	# have your pool map the file names to dataframes
		df_list = pool.map(summed_across_vertices, df_list_cluster_id)
	
	# works on windows 
	#df_list=[]
	#print(df_list)	
	#for thg in df_list_cluster_id:

		#df_list.append(summed_across_vertices(thg,start,end))
	
	combined_df = pd.concat(df_list, ignore_index=True)

	return combined_df


"""
**************************************
*
*
*
*
***************************************
"""

def get_max_rmse(df, index):
	# select it out of the DF
	ind = df[df['index']==index]  # just grab the rows for this index
	# RMSE is actually a string with brackets '[75.3434343]'  
	# So we have to extract it, float it, and then list it before we can max it. 

	max_rmse = np.max(ind['rmse'])   # we have to parse out the RMSE because it's a string
	return {'index': index, 'RMSE_max': max_rmse*1.001}


"""
**************************************
*
*
*
*
***************************************
"""

def ClusterPointCalc(dframe, clusterPoint_id,aicWeight,vScoreWeight):

	#print(clusterPoint_id)

	#aicWeight = 0.296
	#vScoreWeight = 0.886

	these = dframe[dframe['cluster_id']==clusterPoint_id]

	these['rankVscore'] = these['vertscore'].rank(method='max')

	these['rankAICc'] = these['AICc'].rank(method='max', ascending=False)

	#this is where the weights that were determined from interpreters get applied 
	these['combined'] = (these['rankAICc']*aicWeight)+(these['rankVscore']*vScoreWeight)

	these['selected'] = ((these['combined'] == np.max(these['combined']))*100)+1

	return these

"""
**************************************
*
*
*
*
***************************************
"""

def addValuesToNewColumns(index, row, df):

	count = 0

	replace1 = row['params'].replace('=',':')

	if "spikeThreshold:0.75," in replace1:
		df.at[index,'spikeThreshold'] =0.75
		# print(1)
		count+=1
	if "spikeThreshold:0.9," in replace1:
		df.at[index,'spikeThreshold'] =0.9
		# print(2)
		count+=1
	if "spikeThreshold:1," in replace1:
		df.at[index,'spikeThreshold'] =1.0
		# print(3)
		count+=1

	if "maxSegments:6," in replace1:
		df.at[index, 'maxSegments'] = 6
		# print(4)
		count+=1
	if "maxSegments:8," in replace1:
		df.at[index, 'maxSegments'] = 8
		# print(5)
		count+=1
	if "maxSegments:10," in replace1:
		df.at[index,'maxSegments'] = 10
		# print(6)
		count+=1
	if "maxSegments:11," in replace1:
		df.at[index, 'maxSegments'] = 11
		# print(7)
		count+=1

	if "recoveryThreshold:0.25," in replace1:
		df.at[index, 'recoveryThreshold'] =0.25
		# print(8)
		count+=1
	if "recoveryThreshold:0.5," in replace1:
		df.at[index, 'recoveryThreshold'] =0.5
		# print(9)
		count+=1
	if "recoveryThreshold:0.9," in replace1:
		df.at[index, 'recoveryThreshold'] =0.9
		# print(10)
		count+=1
	if "recoveryThreshold:1," in replace1:
		df.at[index, 'recoveryThreshold'] =1.0
		# print(11)
		count+=1

	if "pvalThreshold:0.05," in replace1:
		df.at[index, 'pvalThreshold'] =0.05
		# print(12)
		count+=1
	if "pvalThreshold:0.1," in replace1:
		df.at[index, 'pvalThreshold'] =0.1
		# print(13)
		count+=1
	if "pvalThreshold:0.15," in replace1:
		df.at[index,'pvalThreshold'] =0.15
		# print(14)
		count+=1

	if count != 4:
		print('broke')
		sys.exit() 
	return str(index)+"========="

#__________________________________________

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################


### NEXT ###

"""
**************************************
*main
*
*
*
*
***************************************
"""

def run_param_scoring(csv_dir,njobs,startYear=1990,endYear=2021,aicWeight=0.296,vScoreWeight=0.886):

	df_lis = read_in_CSVs(csv_dir,njobs)
	
	# corrects breakpoint and year arrays by fill missing elements with a correct value. 
	df = pool_summed_vert(df_lis,startYear,endYear,njobs)

	# NEW gets the nuber of unique cluster ids
	# number_of_clusters = len(df.cluster_id.unique())
	unique_clusters = sorted(df.cluster_id.unique())
	
	# change the breakpoint array to columns in dataframe
	arr_to_col(df,startYear,endYear)

	#find the unique indices
	indices = set(df['index'])
	
	#populate a dictionary with the indices as keys and the max rmse
	# as the value
	max_rmse_dict = {}

	for ind in indices: 

		max_rmse_dict[ind] = get_max_rmse(df,ind)['RMSE_max']

	# go through the full dataframe and make a list with the
	# max rmse attached to each item. 

	df_indices = df['index']  # get the full list of indices
	max_rmse_list = [max_rmse_dict[ind] for ind in df_indices]  #make a list of the RMSE max based on that. 

	# now add that list to the data frame
	df['max_rmse']=max_rmse_list

	# fix the RMSE string to numeric type
	df['rmse_num']= df['rmse']

	# Then re-scale the RMSE 
	df['NRMSE']= df['rmse_num']/df['max_rmse']  # does this work? 

	# show it. 
	#df[['NRMSE', 'RMSE', 'rmse_num', 'max_rmse']] #, 'rmse_num', 'max_rmse']

	# score vertex matches.  THIS IS THE MAIN EVENT! 

	#First, extract the vertices as a numpy array to work with
	column_names = df.columns
	vs = [name for name in column_names if ('vert' in name) and (name != 'vert') and (name != 'len_vert')]
	verts_only = df[vs].values #convert to a numpy array
		
	
	#**************************************************
	# Now, rescale all of the vertices by segment count
	# sum across the vertices to get the segment count. 
	segment_count = verts_only.sum(axis=1)-1   # segments = number of vertices minus 1
	df['n_segs']=segment_count

	# print(df.iloc[498]['n_segs'])

	# reshape so there is a ,1 in the shape -- not sure why
	#. but the numpy division needs that.  a
	r=np.reshape(segment_count, (segment_count.shape[0], 1))
	#example:  r.shape = (86400,1) while segment_count.shape=(86400,)

	#rescale all of the vertices by the segment count
	# do this simply by multiplying the matrix by the 
	scaled_count = verts_only #/r    # all vertices are rescaled now

	#Now zero-out the end points, and then
	#set only the ones that have single segments to a non-zero
	# value.  set that value to the max it could be for 
	# two segments -- 0.5 

	scaled_count[:,0]=0
	scaled_count[:,-1]=(segment_count==1)#*(0.5)-------------in loop  
	#**************************************************


	#**************************************************
	# Now loop through points and get scores
	# for a given point, process things

	# first grab the chunks of the DF we will use, 
	#. and also get the unique values to loop over

	ind = df['index']# ------- in loop

	unique_inds = set(ind)# -------- in loop

	point = df['cluster_id']# -------- in loop

	unique_points = set(point)#-------- in loop

	# set up a blank array to hold our accumulating values
	vertscore = point * 0.0  # set up a blank ndarray

	# print(5)

	prop_ind_to_all = 0.5   # set to even weighting. --------- in loop hard code

	# print(len(unique_points))
	
	for this_point in unique_points: # len(unique_points) -> 5000

		#get the total for this point across all indices
		point_matrix = scaled_count[(point==this_point),:]
		sums_by_point_vector= point_matrix.sum(axis=0)

		n_runs = point_matrix.shape[0]  #in theory this should always be the same, so could move this out of the loop
		scaled_sums_by_point_vector = sums_by_point_vector / n_runs


		#Do the same, but by index, and get the score
		#POINT, SINGLE INDEX

		for this_ind in unique_inds:
			# print(f'Doing {str(this_point)} and {this_ind}')
			#do the same for this index
			point_ind_matrix = scaled_count[(ind==this_ind)&(point==this_point),:]
			sums_by_point_ind_vector= point_ind_matrix.sum(axis=0)

			#v2 -- scale by possible number of times it could be picked
			n_runs_ind = point_ind_matrix.shape[0]
			scaled_sums_by_point_ind_vector = sums_by_point_ind_vector / n_runs_ind

			score_matrix = ((point_ind_matrix * scaled_sums_by_point_ind_vector * prop_ind_to_all)+(point_ind_matrix * scaled_sums_by_point_vector * (1-prop_ind_to_all)))*100

			this_vertscore = score_matrix.sum(axis=1)

			#and then assign to the vertscore array that we'll put on the end
			vertscore[(ind==this_ind) & (point==this_point)]=this_vertscore

	df['vertscore']=vertscore




	# **********
	# with the segment counts we can also get the AIC

	goodness= 1-df['NRMSE']  # so a lower NRMSE is better goodness and light
	n_years = len(vs)  #vs was acquired above as the number of vertices

	df['AIC'] = (2*df['n_segs']) -(2*np.log(abs(goodness)))

	df['AICc'] = df['AIC'] + (2*df['n_segs']**2)/(n_years-df['n_segs']-1)


	dfList = []
	c = 0 
	for i in unique_clusters:#list(range(number_of_clusters)):
		# c = c + 1
		if c == 0 :
			newDFpart = ClusterPointCalc(df,i,aicWeight,vScoreWeight)
		else:
			newDFpart2 = ClusterPointCalc(df,i,aicWeight,vScoreWeight)
			dfList.append(newDFpart2)
		c += 1
	result = newDFpart.append(dfList)

	df = result

	for index, row in df.iterrows():

		addValuesToNewColumns(index, row,df)

	output_fn = '/vol/v1/proj/LTOP_FTV_Py/param_selection_testing_outputs/intermediate_testing_output_revised.csv'
	df.to_csv(output_fn, index=False)
	return df

#this was previously from the 02 script and is now integrated here for ease. 
#TODO this is still a very inefficient way of doing this. All of these iterrows calls really need to be removed

###########################################################################################################################

# df = pd.read_csv("/vol/v1/proj/LTOP_mekong/csvs/02_param_selection/selected_param_config_gee_implementation/cambodia_troubleshooting_params_tc.csv")
# outfile = '/vol/v1/proj/LTOP_mekong/csvs/02_param_selection/selected_param_config_gee_implementation/LTOP_Cambodia_troubleshooting_selected_LT_params_tc.csv'
def get_max_mean(df1,col_name): 
    '''
    Calculate the mean of the combined rankVscore and rankAICcscore, considering the weighting factors, 
    for each possible value for a given param. Then take the max mean value. 
    '''
    #this assumes you've already subset by cluster_id as is the case in the param selection code 
    #get the mean by possible param values 
    df1 = pd.DataFrame(df1.groupby([col_name])['combined'].mean()).reset_index()
    #get the max mean value for the given param 
    df2 = df1.loc[df1['combined'] == df1['combined'].max()]
    return df2

def ClusterPointCalc2(dframe, clusterPoint_id):
	all_clust = dframe.loc[dframe['cluster_id'] == clusterPoint_id]
	these = dframe[(dframe['cluster_id']==clusterPoint_id) & (dframe['selected']==101)] #commented out the second part
	# print('These looks like: ')
	# print('==========================================================')
	# print(these)
	# print(these.shape)
	# print(these['index'].unique())

	#right here we have ties and previously we were just taking the first row in the group of ties. 
	#we want to implement a more robust and repeatable method for doing that 
	#TODO not clear if this should indeed be all_clust or if we 
	rec_select = get_max_mean(all_clust,'recoveryThreshold')
	#next do spikeThreshold
	spike_select = get_max_mean(all_clust,'spikeThreshold')
	#then maxSegments
	max_select = get_max_mean(all_clust,'maxSegments')
	#then pvalThreshold 
	pval_select = get_max_mean(all_clust,'pvalThreshold')

	#then do the sequential subsetting, starting with the full dataframe - in the actual code this is a subset of the df for the cluster
	df1 = these.loc[these.recoveryThreshold == rec_select.recoveryThreshold.iloc[0]]
	df2 = df1.loc[df1.spikeThreshold == spike_select.spikeThreshold.iloc[0]]
	df3 = df2.loc[df2.maxSegments == max_select.maxSegments.iloc[0]]
	df4 = df3.loc[df3.pvalThreshold == pval_select.pvalThreshold.iloc[0]]

	# firstOfthese = these.head(1)[['cluster_id','index','params','spikeThreshold','maxSegments','recoveryThreshold','pvalThreshold']]
	print('the selected outputs are going to look like')
	print('==============================================')
	print(df4.shape)
	return df4#firstOfthese        

def generate_selected_params(*args):#csv_dir,njobs,output_file): 
	args = args[0]
	df = run_param_scoring(args['param_scoring_inputs'],args['njobs'],startYear = args['startYear'],endYear = args['endYear'])
	dfList = []
	count = 0 
	#this was changed 3/8/2022 so that it iterates through the kmeans cluster ids and not a chronological list BRP
	for i in sorted(df['cluster_id'].unique()):
		# print('iteration is: ',i)
		# count = count + 1

		if count == 0 :

			newDFpart = ClusterPointCalc2(df,i)

		else:
		
			newDFpart2 = ClusterPointCalc2(df,i)

			dfList.append(newDFpart2)

		count +=1
	result = newDFpart.append(dfList)


	result.to_csv(args['outfile'], index=False)
	print('Done generating selected LT params file')
	return None


#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
# if __name__ == '__main__':
# 	params = ({'param_scoring_inputs':'/vol/v1/proj/LTOP_mekong/csvs/02_param_selection/cambodia_troubleshooting_tc/',
# 			 'njobs':8,
# 			 'startYear':1990,
# 			 'endYear':2021,
# 			 'outfile':'/vol/v1/proj/LTOP_mekong/csvs/02_param_selection/selected_param_config_gee_implementation/python_implementation_testing.csv'
# 			 })

# 	generate_selected_params(params)

# 	### new user args ###
# 	input_dir = "/vol/v1/general_files/user_files/ben/LTOP_FTV_py_revised/output_04_lt_runs/"
# 	startYear = 1990 
# 	endYear = 2021
# 	outfile = "/vol/v1/general_files/user_files/ben/LTOP_FTV_py_revised/selected_lt_params/selected_tc_lt_params.csv"
# 	njobs = 8

# 	main(input_dir,njobs,outfile)
# 	print('complete')
# 	sys.exit()

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

