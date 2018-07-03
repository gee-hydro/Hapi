# -*- coding: utf-8 -*-
"""
Created on Sat Apr 28 21:21:41 2018

@author: Mostafa
"""
# library
import pickle
import numbers
import numpy as np
#import os
import gdal

# functions
def save_obj(obj, saved_name ):
    """
    ===============================================================
        save_obj(obj, saved_name )
    ===============================================================
    this function is used to save any python object to your hard desk
    
    Inputs:
    ----------
        1-obj:
            
        2-saved_name:
            ['String'] name of the object 
    Outputs:    
    ----------
        the object will be saved to the given path/current working directory
        with the given name
    Example:
        data={"key1":[1,2,3,5],"key2":[6,2,9,7]}
        save_obj(data,path+'/flow_acc_table')
    """
    with open( saved_name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(saved_name):
    """
    ===============================================================
        load_obj(saved_name)
    ===============================================================
    this function is used to save any python object to your hard desk
    
    Inputs:
    ----------
        1-saved_name:
            ['String'] name of the object
    Outputs:    
    ----------
        the object will be loaded
    Example:
        load_obj(path+'/flow_acc_table')
    """
    with open( saved_name + '.pkl', 'rb') as f:
        return pickle.load(f)


def get_raster_data(dem):
    """
    _get_mask(dem)
    to create a mask by knowing the stored value inside novalue cells 
    Inputs:
        1- flow path lenth raster
    Outputs:
        1- mask:array with all the values in the flow path length raster
        2- no_val: value stored in novalue cells
    """
    no_val = np.float32(dem.GetRasterBand(1).GetNoDataValue()) # get the value stores in novalue cells
    mask = dem.ReadAsArray() # read all values
    return mask, no_val

def calculateK(x,position,UB,LB):
    '''
    calculateK(x,position,UB,LB):
        this function takes value of x parameter and generate 100 random value of k parameters between
        upper & lower constraint then the output will be the value coresponding to the giving position
        
        Inputs:
            1- x weighting coefficient to determine the linearity of the water surface
                (one of the parameters of muskingum routing method)
            2- position 
                random position between upper and lower bounds of the k parameter
            3-UB 
                upper bound for k parameter
            3-LB 
                Lower bound for k parameter
    '''
    constraint1=0.5*1/(1-x) # k has to be smaller than this constraint
    constraint2=0.5*1/x   # k has to be greater than this constraint
    
    if constraint2 >= UB : #if constraint is higher than UB take UB
        constraint2 =UB
        
    if constraint1 <= LB : #if constraint is lower than LB take UB
        constraint1 =LB
    
    generatedK=np.linspace(constraint1,constraint2,101)
    k=generatedK[int(round(position,0))]
    return k


def par2d_lumpedK1_lake(par_g,raster,no_parameters,no_parameters_lake,kub,klb):
    """
    ===========================================================
      par2d_lumpedK1(par_g,raster,no_parameters,no_par_lake,kub,klb)
    ===========================================================
    this function takes a list of parameters and distribute them horizontally on number of cells
    given by a raster 
    
    Inputs :
        1- par_g
            list of parameters
        2- raster
            raster of the catchment (DEM)
        3- no_parameters
            no of parameters of the cell
        4- no_parameters_lake
            no of lake parameters
        5- kub
            upper bound of K value (traveling time in muskingum routing method)
        6- klb
            Lower bound of K value (traveling time in muskingum routing method)
    Output:
        1- par_2d: 3D array of the parameters distributed horizontally on the cells
        2- lake_par: list of the lake parameters.
    Example:
        a list of 155 value,all parameters are distributed except lower zone coefficient
        (is written at the end of the list) each cell(14 cells) has 11 parameter plus lower zone
        (12 parameters) function will take each 11 parameter and assing them to a specific cell
        then assign the last value (lower zone parameter) to all cells
        14*11=154 + 1 = 155
    """
    # get the shape of the raster
    shape_base_dem = raster.ReadAsArray().shape
    # read the raster    
    f=raster.ReadAsArray()
    # get the no_value of in the raster    
    no_val = np.float32(raster.GetRasterBand(1).GetNoDataValue())
    # count the number of non-empty cells 
    no_elem = np.sum(np.sum([[1 for elem in mask_i if elem != no_val] for mask_i in f]))
    
    # store the indeces of the non-empty cells
    celli=[]#np.ones((no_elem,2))
    cellj=[]
    for i in range(shape_base_dem[0]): # rows
        for j in range(shape_base_dem[1]): # columns
            if f[i,j]!= no_val:
                celli.append(i)
                cellj.append(j)
    
    # create an empty 3D array [[raster dimension], no_parameters]
    par_2d=np.zeros([shape_base_dem[0], shape_base_dem[1], no_parameters])*np.nan
    
    # parameters in array
    # remove a place for the lumped parameter (k1) lower zone coefficient    
    no_parameters=no_parameters-1
    
    # create a 2d array [no_parameters, no_cells]
    par_arr=np.ones((no_parameters,no_elem))
    
    # take the parameters from the generated parameters or the 1D list and 
    # assign them to each cell
    for i in range(no_elem):
        par_arr[:,i] = par_g[i*no_parameters:(i*no_parameters)+no_parameters]
    
    # create a list with the value of the lumped parameter(k1)
    # (stored at the end of the list of the parameters)
    pk1=np.ones((1,no_elem))*par_g[(np.shape(par_arr)[0]*np.shape(par_arr)[1])]
    
    # put the list of parameter k1 at the 6 row
    par_arr=np.vstack([par_arr[:6,:],pk1,par_arr[6:,:]])
    
    # assign the parameters from the array (no_parameters, no_cells) to 
    # the spatially corrected location in par2d
    for i in range(no_elem):
        par_2d[celli[i],cellj[i],:]=par_arr[:,i]
    
    # calculate the value of k(travelling time in muskingum based on value of 
    # x and the position and upper, lower bound of k value 
    for i in range(no_elem):
        par_2d[celli[i],cellj[i],-2]= calculateK(par_2d[celli[i],cellj[i],-1],par_2d[celli[i],cellj[i],-2],kub,klb)

    
    # lake parameters        
    lake_par=par_g[len(par_g)-no_parameters_lake:]
    lake_par[-2]=calculateK(lake_par[-1],lake_par[-2],kub,klb)
    
    return par_2d,lake_par


def par3d(par_g,raster,no_parameters,no_lumped_par=0,lumped_par_pos=[],
                   kub=1,klb=0.5):
    """
    ===========================================================
      par3d(par_g,raster, no_parameters, no_lumped_par, lumped_par_pos, kub, klb)
    ===========================================================
    this function takes a list of parameters [saved as one column or generated
    as 1D list from optimization algorithm] and distribute them horizontally on
    number of cells given by a raster
    
    Inputs :
    ----------
        1- par_g:
            [list] list of parameters
        2- raster:
            [gdal.dataset] raster to get the spatial information of the catchment
            (DEM, flow accumulation or flow direction raster)
        3- no_parameters
            [int] no of parameters of the cell according to the rainfall runoff model
        4-no_lumped_par:
            [int] nomber of lumped parameters, you have to enter the value of 
            the lumped parameter at the end of the list, default is 0 (no lumped parameters)
        5-lumped_par_pos:
            [List] list of order or position of the lumped parameter among all
            the parameters of the lumped model (order starts from 0 to the length 
            of the model parameters), default is [] (empty), the following order
            of parameters is used for the lumped HBV model used
            [ltt, utt, rfcf, sfcf, ttm, cfmax, cwh, cfr, fc, beta, e_corr, etf, lp,
            c_flux, k, k1, alpha, perc, pcorr, Kmuskingum, Xmuskingum]
        6- kub:
            [float] upper bound of K value (traveling time in muskingum routing method)
            default is 1 hour 
        7- klb:
            [float] Lower bound of K value (traveling time in muskingum routing method)
            default is 0.5 hour (30 min)
    
    Output:
    ----------
        1- par_3d: 3D array of the parameters distributed horizontally on the cells
        
    Example:
    ----------
        EX1:totally distributed parameters
            [fc, beta, etf, lp, c_flux, k, k1, alpha, perc, pcorr, Kmuskingum, Xmuskingum]    
            no_lumped_par=0
            lumped_par_pos=[]
            par_g=np.random.random(no_elem*(no_parameters-no_lumped_par))
        EX2: One Lumped Parameter [K1]
            given values of parameters are of this order
            [fc, beta, etf, lp, c_flux, k, alpha, perc, pcorr, Kmuskingum, Xmuskingum,k1] 
            K1 is lumped so its value is inserted at the end and its order should 
            be after K 
            no_lumped_par=1
            lumped_par_pos=[6]
            par_g=np.random.random(no_elem* (no_parameters-no_lumped_par))
            # insert the value of k1 at the end 
            par_g=np.append(par_g,55)
        EX3:Two Lumped Parameter [K1, Perc]
            no_lumped_par=2
            lumped_par_pos=[6,8]
            par_g=np.random.random(no_elem* (no_parameters-no_lumped_par))
            par_g=np.append(par_g,55)
            par_g=np.append(par_g,66)
    """
    # input data validation
    # data type
    assert type(raster)==gdal.Dataset, "raster should be read using gdal (gdal dataset please read it using gdal library) "
    assert type(par_g)==np.ndarray or type(par_g)==list, "par_g should be of type 1d array or list"
    assert type(no_parameters)==int, " no_parameters should be integer number"
    assert isinstance(kub,numbers.Number) , " kub should be a number"
    assert isinstance(klb,numbers.Number) , " klb should be a number"
    assert type(no_lumped_par)== int, "no of lumped parameters should be integer"
    
    if no_lumped_par>=1:
        if type(lumped_par_pos)==list:
            assert no_lumped_par==len(lumped_par_pos), "you have to entered"+str(no_lumped_par)+"no of lumped parameters but only"+str(len(lumped_par_pos))+" position "
        else: # if not int or list
            assert 1==5 ,"you have one lumped parameters so the position has to be entered as a list"        
#    elif no_lumped_par > 1:
#        assert type(lumped_par_pos)==list, "you have one lumped parameters so the position can be entered as an integer number or in a list"
    
    # get the shape of the raster
    shape_base_dem = raster.ReadAsArray().shape
    # read the raster    
    raster_A=raster.ReadAsArray()
    # get the no_value of in the raster    
    no_val = np.float32(raster.GetRasterBand(1).GetNoDataValue())
    # count the number of non-empty cells 
    no_elem = np.size(raster_A[:,:])-np.count_nonzero((raster_A[raster_A==no_val])) 
    
    # input values
    if no_lumped_par > 0:
        assert len(par_g)==(no_elem*(no_parameters-no_lumped_par))+no_lumped_par,"As there is "+str(no_lumped_par)+" lumped parameters, length of input parameters should be "+str(no_elem)+"*"+"("+str(no_parameters)+"-"+str(no_lumped_par)+")"+"+"+str(no_lumped_par)+"="+str(no_elem*(no_parameters-no_lumped_par)+no_lumped_par)+" not "+str(len(par_g))+" probably you have to add the value of the lumped parameter at the end of the list"
    else:
        # if there is no lumped parameters
        assert len(par_g)==no_elem*no_parameters,"As there is no lumped parameters length of input parameters should be "+str(no_elem)+"*"+str(no_parameters)+"="+str(no_elem*no_parameters)
    
    # store the indeces of the non-empty cells
    celli=[]#np.ones((no_elem,2))
    cellj=[]
    for i in range(shape_base_dem[0]): # rows
        for j in range(shape_base_dem[1]): # columns
            if raster_A[i,j]!= no_val:
                celli.append(i)
                cellj.append(j)
    
    # create an empty 3D array [[raster dimension], no_parameters]
    par_2d=np.zeros([shape_base_dem[0], shape_base_dem[1], no_parameters])*np.nan
    
    # parameters in array
    # remove a place for the lumped parameter (k1) lower zone coefficient    
    no_parameters=no_parameters-no_lumped_par
    
    # create a 2d array [no_parameters, no_cells]            
    par_arr=np.ones((no_parameters,no_elem))
    
    # take the parameters from the generated parameters or the 1D list and 
    # assign them to each cell
    for i in range(no_elem):
        par_arr[:,i] = par_g[i*no_parameters:(i*no_parameters)+no_parameters]
    
    ### lumped parameters
    if no_lumped_par > 0:
        for i in range(no_lumped_par):
            # create a list with the value of the lumped parameter(k1)
            # (stored at the end of the list of the parameters)
            pk1=np.ones((1,no_elem))*par_g[(no_parameters*np.shape(par_arr)[1])+i]
            # put the list of parameter k1 at the 6 row    
            par_arr=np.vstack([par_arr[:lumped_par_pos[i],:],pk1,par_arr[lumped_par_pos[i]:,:]])
    
    # assign the parameters from the array (no_parameters, no_cells) to 
    # the spatially corrected location in par2d
    for i in range(no_elem):
        par_2d[celli[i],cellj[i],:]=par_arr[:,i]
    
    # calculate the value of k(travelling time in muskingum based on value of 
    # x and the position and upper, lower bound of k value 
    for i in range(no_elem):
        par_2d[celli[i],cellj[i],-2]= calculateK(par_2d[celli[i],cellj[i],-1],par_2d[celli[i],cellj[i],-2],kub,klb)
    
    return par_2d

def HRU():
    """
    
    
    """