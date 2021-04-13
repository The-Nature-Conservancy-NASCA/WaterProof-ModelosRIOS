#!/usr/bin/env python
# -*- coding: utf-8 -*-


# Date: 14/12/2020
# Author: Diego Rodriguez - Skaphe Tecnologia SAS
# WFApp
import logging
import sys, os, rasterio, fiona, ogr, osr, datetime
from rasterio.mask import mask
from zonalStatistics import calculateRainfallDayMonth,calculateStatistic
from createBioParamCsv import getColsParams,generateCsv,readCsv
sys.path.append('config')
from config import config
from connect import connect
sys.path.append(os.path.split(os.getcwd())[0] + os.path.sep + 'RIOS_Toolbox')
import RIOS_Toolbox.rios_preprocessor as Pro
import RIOS_Toolbox.rios as rios
import re
logger = logging.getLogger('execRios')
logger.setLevel(logging.DEBUG)
# Correspondencia/homologacion entre objetivos de rios_preprocessor y rios
objectives_mapping = {
    'erosion_drinking_control': 'do_erosion',
    'erosion_reservoir_control': 'do_erosion',
    'nutrient_retention_nitrogen': 'do_nutrient_n',
    'nutrient_retention_phosporus': 'do_nutrient_p',
    'flood_mitigation_impact': 'do_flood',
    'groundwater_recharge': 'do_gw_bf',
    'baseflow': 'do_gw_bf'
}

# Exportar poligonos de actividades a shapefile
def exportToShpActivities(path, user):
	params = config(section='postgresql_alfa')
	connString = "PG: host=" + params['host'] + " dbname=" + params['database'] + " user=" + params['user'] + " password=" + params['password'] 
	conn=ogr.Open(connString)
	if conn is None:
		print('Could not open a database or GDAL is not correctly installed!')
		sys.exit(1)

	output = os.path.join(path,"activities_shp")
	print(output)
	source = osr.SpatialReference()
	source.ImportFromEPSG(4326)
	target = osr.SpatialReference()
	target.ImportFromEPSG(3857)
	transform = osr.CoordinateTransformation(source, target)

	# Schema definition of SHP file
	out_driver = ogr.GetDriverByName( 'ESRI Shapefile' )
	if os.path.exists(output):
		out_driver.DeleteDataSource(output)

	out_ds = out_driver.CreateDataSource(output)

	

	out_layer = out_ds.CreateLayer("activities", target, ogr.wkbMultiPolygon)
	fd_activity = ogr.FieldDefn('activity_n',ogr.OFTString)
	fd_action = ogr.FieldDefn('action',ogr.OFTString)
	out_layer.CreateField(fd_activity)
	out_layer.CreateField(fd_action)
	# if(len(catchment) == 1):
	# 	params = ' = ' + str(catchment[0]) 
	# elif(len(catchment) > 1):
	# 	params = ' IN ('
	# 	for c in catchment:
	# 		params = params + str(c) + ','
	# 	params = params[:-1] + ')'



	# sql = "select getactivityshp(" +  str(user) + ")"
	sql = ("select shp.id,nbs.name,shp.action,shp.area"
            " from waterproof_nbs_ca_waterproofnbsca nbs"
            " join waterproof_nbs_ca_activityshapefile shp on nbs.activity_shapefile_id = shp.id"
            " where nbs.added_by_id = " +  str(user) + ";")

	print(sql)

    # layer = conn.GetLayerByName("delineated_catchment")
	layer = conn.ExecuteSQL(sql)
    
	feat = layer.GetNextFeature()
	while feat is not None:
		# print(feat)
		featDef = ogr.Feature(out_layer.GetLayerDefn())
		geom = feat.GetGeometryRef()
		geom.Transform(transform)		
		featDef.SetGeometry(geom)			
		featDef.SetField('activity_n',remove_accents(feat.name))		
		featDef.SetField('action',feat.action)		
		out_layer.CreateFeature(featDef)
		feat.Destroy()
		feat = layer.GetNextFeature()
        

	conn.Destroy()
	out_ds.Destroy()
		
	return output

def resamplingRaster(templatePath,srcPath,out):

    # Source
    src = gdal.Open(srcPath, gdalconst.GA_ReadOnly)
    src_proj = src.GetProjection()
    src_geotrans = src.GetGeoTransform()

    print(templatePath)
    # We want a section of source that matches this:
    match_ds = gdal.Open(templatePath, gdalconst.GA_ReadOnly)
    match_proj = match_ds.GetProjection()
    match_geotrans = match_ds.GetGeoTransform()
    wide = match_ds.RasterXSize
    high = match_ds.RasterYSize

    # Output / destination
    dst = gdal.GetDriverByName('Gtiff').Create(out, wide, high, 1, gdalconst.GDT_Float32)
    dst.SetGeoTransform( match_geotrans )
    dst.SetProjection( match_proj)

    # Do the work
    gdal.ReprojectImage(src, dst, src_proj, match_proj, gdalconst.GRA_NearestNeighbour)

    del dst # Flush

    print ("finish")



# Obtener parametros de modelo
def getParameters(basin,model):
    logger.debug("getParameters")
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('getparametersmodel',[basin,model])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
    cursor.close()
    return listResult

# Recuperar macroregion por id
def getRegionFromId(basin):
	result = ''
	cursor = connect('postgresql_alfa').cursor()
	cursor.callproc('getBasin',[basin])
	result = cursor.fetchall()
	for row in result:
		result = row
	cursor.close()
	return result

# Recuperar constante por macroregion
def getConstantFromBasin(basin,constantName):
	result = ''
	cursor = connect('postgresql_alfa').cursor()
	cursor.callproc('getconstant',[basin,constantName])
	result = cursor.fetchall()
	for row in result:
		result = row
	cursor.close()
	return result

# Cortar raster
def cutRaster(catchment,path,out_path):
	data = rasterio.open(path)
	with fiona.open(catchment, "r") as shapefile:
		shapes = [feature["geometry"] for feature in shapefile]
	
	with rasterio.open(path) as src:
		#if 'Stream' in path or 'Soil_Depth' in path:
		#	nd = 255
		#else:
		#	nd = -999

		out_image, out_transform = mask(src, shapes, crop=True)
		out_meta = src.meta

        print(path)

        out_meta.update({"driver": "GTiff",
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform})



        # if "RainfallDay" not in path:
        #     out_meta.update({"driver": "GTiff",
        #             "height": out_image.shape[1],
        #             "width": out_image.shape[2],
        #             "transform": out_transform,
        #             "nodata":-9999})

        # if "Stream" in path:
        #     out_meta.update({"driver": "GTiff",
        #         "height": out_image.shape[1],
        #         "width": out_image.shape[2],
        #         "transform": out_transform,
        #         "nodata":-9999})
        # else:  
        #     out_meta.update({"driver": "GTiff",
        #     "height": out_image.shape[1],
        #     "width": out_image.shape[2],
        #     "transform": out_transform})
	

    
	
	with rasterio.open(os.path.join(out_path,os.path.basename(path)), "w", **out_meta) as dest:
		dest.write(out_image)

	return os.path.join(out_path,os.path.basename(path))

def getActivities(user_id):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('getactivities',[user_id])
    result = cursor.fetchall()
    for row in result:
        # print(row)
        listResult.append(row)
    cursor.close()
    return listResult

def getTransitions():
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('gettransitions',[])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
    cursor.close()
    return listResult

def getParametersByObj(id_obj, id_basin):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('getparametersbyobj',[id_basin,id_obj])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
    cursor.close()
    return listResult

def getActivityShapefile(user_id):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('getactivityshp',[user_id])
    result = cursor.fetchall()
    for row in result:
        # print(row)
        listResult.append(row)
    cursor.close()
    return listResult

def getObjectives(ids):
    listResult = []
    for id in ids:
        cursor = connect('postgresql_alfa').cursor()
        cursor.callproc('getobjectives',[id])
        result = cursor.fetchall()
        for row in result:
            listResult.append(row)
        cursor.close()
    
    return listResult



# Procesar parametros
def processParameters(parametersList, basin, pathF, user, objectives, inputs_objs, outPreProc, catchment):
# def processParameters(parametersList, basin, catchment,pathF, user):
    dictParameters = dict()
    out_path = ""
    in_path = ""
    out_folder = parametersList[0][9]
    out_path = os.path.join(os.getcwd(),pathF,'out',out_folder)
    in_path = os.path.join(os.getcwd(),pathF,'in',out_folder)
	
    measurement_value = 10000
    measurement_unit = "area"

    isdir = os.path.isdir(out_path)
    if(not isdir):
        os.mkdir(out_path)

    isdir = os.path.isdir(in_path)
    if(not isdir):
        os.mkdir(in_path)

    for parameter in parametersList:
        name = parameter[0]
        value = parameter[1]
        if(value == 'False'):
            value = False
        elif(value == 'True'):
            value = True
        cut = parameter[2]
        constant = parameter[3]
        suffix = parameter[4]
        empty = parameter[5]
        file = parameter[6]
        folder = parameter[7]
        outPathType = parameter[8]
        calculado = parameter[11]
        inputUser = parameter[12]
        bio_param = parameter[13]
        preproc = parameter[14]
        riosType = parameter[15]

        # print(riosType)
        if(riosType):
            # print(riosType)
            if(riosType == 'activities'):
                dictParameters[name] = {}
                listAct = getActivities(user)
                # print(listAct) 
                for la in listAct:
                    dictParameters[name][remove_accents(la[0])] = {}
                    dictParameters[name][remove_accents(la[0])]["measurement_unit"] = measurement_unit
                    dictParameters[name][remove_accents(la[0])]["measurement_value"] = measurement_value
                    dictParameters[name][remove_accents(la[0])]["unit_cost"] = float(la[1] + la[2])
                    
                value = dictParameters[name]

            elif(riosType == 'transition_default'):
                dictParameters[name] = []
                listTrans = getTransitions()
                for lt in listTrans:
                    dictTran = {
                        "file_name": lt[1],
                        "transition_type": lt[2],
                        "id": lt[3],
                        "label": lt[4]
                    }
                    dictParameters[name].append(dictTran)

                value = dictParameters[name]
            
            elif(riosType == 'shp_act'):
                dictParameters[name] = []
                listAct = []
                listPolygons = getActivityShapefile(user)
                outShp = exportToShpActivities(in_path, user)
                listAct.append(outShp)           
                value = listAct  

            elif(riosType == 'transition_map'):
                dictParameters[name] = {}
                transitionsList = getTransitions()
                for transition in transitionsList:
                    dictParameters[name][transition[1]] = {}
                    listActivities = getActivities(user)
                    for activity in listActivities:
                        dictParameters[name][transition[1]][remove_accents(activity[0])] = 0
                value = dictParameters[name]
            
            elif(riosType == 'lulc_act'):
                key_lulc = "lulc_coefficients_table_uri"
                dictParameters[name] = {}
                file = ""
                listActivities_1 = getActivities(user)
                
                if(key_lulc not in dictParameters):
                    # print("no existe no")
                    region = getRegionFromId(basin)
                    label = region[4]
                    file = os.path.join(os.getcwd(),pathF,'in',"biophysical_table.csv")
                    values,headers = getColsParams("apps.skaphe.com",27017,"waterProof","parametros_biofisicos",user,label,True)
                    generateCsv(headers,values,file)
                    value = file

                listCsv = readCsv(file,"lucode")
                for lulc in listCsv:
                    dictParameters[name][lulc] = []
                    list_la = []
                    # print(listActivities_1)
                    for act in listActivities_1:     
                                          
                        list_la.append(remove_accents(act[0]))
                
                    # print(list_la)
                    dictParameters[name][lulc] = list_la

                value = dictParameters[name]

            elif(riosType == "priorities"):
                dictParameters[name] = {}
                transitionsList = getTransitions()
                for transition in transitionsList:
                    dictParameters[name][transition[1]] = {}
                    listObjectives = getObjectives(objectives)
                    for obj in listObjectives:
                        dictParameters[name][transition[1]][obj[0]] = 1

                value = dictParameters[name]
                # print(listCsv)

            elif(riosType == "budget_conf"):
                dictParameters[name] = {}
                dictParameters[name]["years_to_spend"] = 10  # Parametro a sustituir por el numero de años
                dictParameters[name]["activity_budget"] = {}
                listAct = getActivities(user)
                # print(listAct) 
                for la in listAct:
                    dictParameters[name]["activity_budget"][remove_accents(la[0])] = {}
                    dictParameters[name]["activity_budget"][remove_accents(la[0])]["budget_amount"] = 10000 # sustituir

                dictParameters[name]["if_left_over"] = "Report remainder"
                dictParameters[name]["floating_budget"] = 999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999  # Sustituir

                value = dictParameters[name]

            elif(riosType == "objectives"):
                dictParameters[name] = {}
                listObjectives = getObjectives(objectives)
                for obj in listObjectives:
                    dictParameters[name][obj[0]] = {}
                    dictParameters[name][obj[0]]["rios_model_type"] = "rios_tier_0"
                    dictParameters[name][obj[0]]["priorities"] = {}
                    transitionsList = getTransitions()
                    listParametersObj = getParametersByObj(obj[1], basin)
                    for transition in transitionsList:
                        dictParameters[name][obj[0]]["priorities"][transition[1]] = {}
                        for param in listParametersObj:
                            dictParameters[name][obj[0]]["priorities"][transition[1]][param[0]] = 0

                    dictParameters[name][obj[0]]["factors"] = {}

                    for param in listParametersObj:
                        region = getRegionFromId(basin)
                        label = region[4]
                        if(param[0] == 'Vegetative Cover Index' or param[0] == 'Land Use Land Cover Retention at pixel' 
                        or param[0] == 'On-pixel retention' or param[0] == 'On-pixel source'):
                            ranks = {
                                'Vegetative Cover Index': 'Cover_Rank',
                                'Land Use Land Cover Retention at pixel':'Rough_Rank',
                                'On-pixel retention':'Sed_Ret',
                                'On-pixel source': 'Sed_Exp'
                            }
                            
                            file = os.path.join(os.getcwd(),pathF,'in',"biophysical_table.csv")
                            values,headers = getColsParams("apps.skaphe.com",27017,"waterProof","parametros_biofisicos",user,label,True)
                            generateCsv(headers,values,file)
                            # value = file
                            dictParameters[name][obj[0]]["factors"][param[0]] = {}
                            dictParameters[name][obj[0]]["factors"][param[0]]["bins"] = {}
                            dictParameters[name][obj[0]]["factors"][param[0]]["bins"]["key_field"] = 'lulc_general'
                            dictParameters[name][obj[0]]["factors"][param[0]]["bins"]["raster_uri"] = param[2]
                            dictParameters[name][obj[0]]["factors"][param[0]]["bins"]["uri"] = file
                            dictParameters[name][obj[0]]["factors"][param[0]]["bins"]["value_field"] = ranks[param[0]]
                        else:
                            
                            if inputs_objs[objectives_mapping[obj[0]]].has_key(param[0]):
                                dictParameters[name][obj[0]]["factors"][param[0]] = {}
                                dictParameters[name][obj[0]]["factors"][param[0]]["raster_uri"] = os.path.join(outPreProc,inputs_objs[objectives_mapping[obj[0]]][param[0]].format(label))
                                dictParameters[name][obj[0]]["factors"][param[0]]["bins"] = {}
                                dictParameters[name][obj[0]]["factors"][param[0]]["bins"]["inverted"] = False
                                dictParameters[name][obj[0]]["factors"][param[0]]["bins"]["type"] = "interpolated"
                                dictParameters[name][obj[0]]["factors"][param[0]]["bins"]["interpolation"] = "linear"
                            else:
                            # print(objectives_mapping[obj[0]])
                            # print(inputs_objs)
                                dictParameters[name][obj[0]]["factors"][param[0]] = {}
                                dictParameters[name][obj[0]]["factors"][param[0]]["raster_uri"] = param[2]
                                dictParameters[name][obj[0]]["factors"][param[0]]["bins"] = {}
                                dictParameters[name][obj[0]]["factors"][param[0]]["bins"]["inverted"] = False
                                dictParameters[name][obj[0]]["factors"][param[0]]["bins"]["type"] = "interpolated"
                                dictParameters[name][obj[0]]["factors"][param[0]]["bins"]["interpolation"] = "linear"


                value = dictParameters[name]


                



                # if(dictParameters["lulc_activity_potential_map"]):
                #     print("existe")
                # else:
                #     print("no existe")

                # dictParameters[name] = {}
                # transitionsList = getTransitions()
                # for transition in transitionsList:
                #     dictParameters[name][transition[1]] = {}
                #     listActivities = getActivities(user)
                #     for activity in listActivities:
                #         dictParameters[name][transition[1]][remove_accents(activity[0])] = 0
                # value = dictParameters[name]
                
        
        if(outPathType):
            value = out_path

        if(bio_param):
            # print("bio_param: " + name)
            region = getRegionFromId(basin)
            label = region[4]
            file = os.path.join(os.getcwd(),pathF,'in',"biophysical_table.csv")
            values,headers = getColsParams("apps.skaphe.com",27017,"waterProof","parametros_biofisicos",user,label,True)
            generateCsv(headers,values,file)
            value = file

        if(cut):
            value = cutRaster(catchment,value,in_path)



        
        dictParameters[name] = value
        

                





        # if(suffix):
        #     region = getRegionFromId(basin)
        #     label = region[4]
        #     value = label
        # if(constant):
        #     constantValue = getConstantFromBasin(basin,name)
        #     value = constantValue[2]
        # if(empty):
        #     value = ''
        # if(cut):
        #     value = cutRaster(catchment,value,in_path)
        # if(file):
        #     value = catchment
        # if(outPathType):
        #     value = out_path
        # if(calculado):
        #     region = getRegionFromId(basin)
        #     label = region[4]
        #     maxMonth,outRaster = calculateRainfallDayMonth(value,catchment,label)
        #     value = cutRaster(catchment,outRaster,in_path)
        # if(inputUser):
        #     value = inputs[name]
        # if(bio_param):
		# 	region = getRegionFromId(basin)
		# 	label = region[4]
		# 	file = os.path.join(os.getcwd(),pathF,'in',"biophysical_table.csv")
		# 	values,headers = getColsParams("apps.skaphe.com",27017,"waterProof","parametros_biofisicos",user,label,True)
		# 	generateCsv(headers,values,file)
		# 	value = file
        # dictParameters[name] = value
        # print(parameter)


    for parameter in parametersList:
        # name = parameter[0]
        # value = parameter[1]
        # if(value == 'False'):
        #     value = False
        # elif(value == 'True'):
        #     value = True
        # cut = parameter[2]
        # constant = parameter[3]
        # suffix = parameter[4]
        # empty = parameter[5]
        # file = parameter[6]
        # folder = parameter[7]
        # outPathType = parameter[8]
        # calculado = parameter[11]
        # inputUser = parameter[12]
        # if(suffix):
        #     region = getRegionFromId(basin)
        #     label = region[4]
        #     value = label
        # if(constant):
        #     constantValue = getConstantFromBasin(basin,name)
        #     value = constantValue[2]
        # if(empty):
        #     value = ''
        # if(cut):
        #     value = cutRaster(catchment,value,in_path)
        # if(file):
        #     value = catchment
        # if(outPathType):
        #     value = out_path
        # # if(calculado):
        #     # region = getRegionFromId(basin)
        #     # label = region[4]
        #     # maxMonth,outRaster = calculateRainfallDayMonth(value,catchment,label)
        #     # value = cutRaster(catchment,outRaster,in_path)
        # # if(inputUser):
        # #     value = inputs[name]

        # dictParameters[name] = value
    # print(value)

    
	return dictParameters,out_path

def executeFunction(basin,id_catchment,id_usuario,inputs):
    date = datetime.date.today()
    path = os.path.join("/home/skaphe/Documentos/tnc/modelos/Workspace_BasinDelineation/tmp",str(id_usuario) +  "_" + str(date.year) + "_" + str(date.month) + "_" + str(date.day))
    pathPreprocIn = os.path.join(path,"in","02-PREPROC_RIOS")
    pathPreprocOut = os.path.join(path,"out","02-PREPROC_RIOS")
    pathCatchment = os.path.join(path,"in","catchment")


    isdir = os.path.isdir(path)
    if(not isdir):
        os.mkdir(path)
        os.mkdir(os.path.join(path,"in"))
        os.mkdir(os.path.join(path,"out"))

    isdir = os.path.isdir(os.path.join(path,"in"))
    if(not isdir):
        os.mkdir(os.path.join(path,"in"))

    isdir = os.path.isdir(os.path.join(path,"out"))
    if(not isdir):
        os.mkdir(os.path.join(path,"out"))

    isdir = os.path.isdir(pathPreprocIn)
    if(not isdir):
        os.mkdir(pathPreprocIn)

    isdir = os.path.isdir(pathPreprocOut)
    if(not isdir):
        os.mkdir(pathPreprocOut)

    isdir = os.path.isdir(pathCatchment)
    if(not isdir):
        os.mkdir(pathCatchment)
    
    list = getParameters(basin,'preprocRIOS')
    catchment = exportToShp(id_catchment,path)
    parameters,out_path = processParameters(list, basin, catchment,path,inputs,id_usuario)

    print(parameters)

    Pro.main(   working_path                = parameters["working_path"],
            output_path                 = parameters["output_path"] ,
            hydro_path                  = parameters["hydro_path"],
            rios_coeff_table            = parameters["rios_coeff_table"],
            lulc_raster_uri             = parameters["lulc_raster_uri"],
            dem_raster_uri              = parameters["dem_raster_uri"],
            erosivity_raster_uri        = parameters["erosivity_raster_uri"],
            erodibility_raster_uri      = parameters["erodibility_raster_uri"],
            soil_depth_raster_uri       = parameters["soil_depth_raster_uri"],
            precip_month_raster_uri     = parameters["precip_month_raster_uri"],
            soil_texture_raster_uri     = parameters["soil_texture_raster_uri"],
            precip_annual_raster_uri    = parameters["precip_annual_raster_uri"],
            aet_raster_uri              = parameters["aet_raster_uri"],
            suffix                      = parameters["suffix"],
            aoi_shape_uri               = parameters["aoi_shape_uri"],
            streams_raster_uri          = parameters["streams_raster_uri"],
            do_erosion          = parameters["do_erosion"], # Objetivo de aporte de sedimentos para reservorios y sistemas de tratamiento
            do_nutrient_p       = parameters["do_nutrient_p"], # Objetivo nutrientes Fosforo
            do_nutrient_n       = parameters["do_nutrient_n"], # Objetivo nutrientes Nitrogeno
            do_flood            = parameters["do_flood"], # Objetivo control de inundaciones
            do_gw_bf            = parameters["do_gw_bf"], # Objetivo recarga de agua subterranea y flujo base
            river_buffer_dist   = int(parameters["river_buffer_dist"])) # Buffer


def remove_accents(string):
    if type(string) is not unicode:
        string = unicode(string, encoding='utf-8')

    string = re.sub(u"[àáâãäå]", 'a', string)
    string = re.sub(u"[èéêë]", 'e', string)
    string = re.sub(u"[ìíîï]", 'i', string)
    string = re.sub(u"[òóôõö]", 'o', string)
    string = re.sub(u"[ùúûü]", 'u', string)
    string = re.sub(u"[ýÿ]", 'y', string)

    return string

def execModel(args):
    logger.debug("execModel :: args :: %s", args)
    rios.execute(args)




# def executeFunction(basin,model,type,id_catchment,id_usuario):
# 	date = datetime.date.today()
# 	path = createFolder(id_usuario,date)

# 	list = getParameters(basin,model)	
# 	catchment = exportToShp(id_catchment, path)
# 	parameters,pathF,label = processParameters(list,basin,catchment,path,type,model)
	

# 	if(model == 'awy'):
# 		awy.execute(parameters)
# 	elif(model == 'sdr'):
# 		sdr.execute(parameters)
# 	elif(model == 'carbon'):
# 		carbon.execute(parameters)
# 	elif(model == 'ndr'):
# 		ndr.execute(parameters)
# 	elif(model == 'swy'):
# 		swy.execute(parameters)

# 	return catchment,path,label


# listP = getParameters(26,'preprocRIOS')
# inputs = {"do_erosion":True,"do_nutrient_p":True,"do_nutrient_n":True,"do_flood":True,"do_gw_bf":True}
# # catchment = exportToShp([6], "/home/skaphe/Documentos/tnc/modelos/Workspace_BasinDelineation/tmp/9_2020_10_24/")
# # parameters,out_path = processParameters(listP,26,catchment,"/home/skaphe/Documentos/tnc/modelos/Workspace_BasinDelineation/tmp/9_2020_10_24/",inputs)
# # print(out_path)
# # print(parameters)
# executeFunction(44,[3],1,inputs)

# listP = getParameters(44,'rios')
# # catchment = exportToShp([3], "/home/skaphe/Documentos/tnc/modelos/Workspace_BasinDelineation/tmp/9_2020_10_24/")
# # parameters,out_path = processParameters(listP,44,catchment,"/home/skaphe/Documentos/tnc/modelos/Workspace_BasinDelineation/tmp/9_2020_10_24/",1000)
# objectives = [2,3,4,5,6,7,8]
# parameters,out_path = processParameters(listP,44,"/home/skaphe/Documentos/tnc/modelos/salidas/9_2020_10_24/",1000,objectives)
# print(parameters)
# execModel(parameters)


# for l in listP:
#     print(l)
# print(listP)