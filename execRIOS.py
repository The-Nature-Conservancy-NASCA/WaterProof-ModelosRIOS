#!/usr/bin/env python
# -*- coding: utf-8 -*-


# Date: 14/12/2020
# Author: Diego Rodriguez - Skaphe Tecnologia SAS
# WFApp
import logging,math
import sys, os, rasterio, fiona, ogr, osr, datetime
from rasterio.mask import mask
from zonalStatistics import calculateRainfallDayMonth,calculateStatistic
from createBioParamCsv import getColsParams,generateCsv,readCsv,getDefaultBiophysicParams,getUserBiophysicParams,filterCsvLucode
sys.path.append('config')
from config import config
from connect import connect
sys.path.append(os.path.split(os.getcwd())[0] + os.path.sep + 'RIOS_Toolbox')
import RIOS_Toolbox.rios_preprocessor as Pro
import RIOS_Toolbox.rios as rios
import re
import json
import exec_preproc

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


def exportToShpActivities(nbsList, path, user):
    params = config(section='postgresql_alfa')
    connString = "PG: host=" + params['host'] + " dbname=" + params['database'] + \
        " user=" + params['user'] + " password=" + params['password']
    conn = ogr.Open(connString)
    if conn is None:
        print('Could not open a database or GDAL is not correctly installed!')
        sys.exit(1)

    # output = os.path.join(path, "activities_shp")
    # print(output)
    # source = osr.SpatialReference()
    # source.ImportFromEPSG(4326)
    # target = osr.SpatialReference()
    # target.ImportFromEPSG(3857)
    # transform = osr.CoordinateTransformation(source, target)

    # # Schema definition of SHP file
    # out_driver = ogr.GetDriverByName('ESRI Shapefile')
    # if os.path.exists(output):
    #     out_driver.DeleteDataSource(output)

    # out_ds = out_driver.CreateDataSource(output)

    # out_layer = out_ds.CreateLayer("activities", target, ogr.wkbMultiPolygon)
    # fd_activity = ogr.FieldDefn('activity_n', ogr.OFTString)
    # fd_action = ogr.FieldDefn('action', ogr.OFTString)
    # out_layer.CreateField(fd_activity)
    # out_layer.CreateField(fd_action)
    # if(len(catchment) == 1):
    # 	params = ' = ' + str(catchment[0])
    # elif(len(catchment) > 1):
    # 	params = ' IN ('
    # 	for c in catchment:
    # 		params = params + str(c) + ','
    # 	params = params[:-1] + ')'

    # sql = "select getactivityshp(" +  str(user) + ")"
    sqlParam='ARRAY['
    for idx,nbs in enumerate(nbsList):
        if (idx<len(nbsList)-1):
            sqlParam=sqlParam+str(nbs[0])+","
        else:
             sqlParam=sqlParam+str(nbs[0])+"]"
        print(sqlParam)

    sql = ("select shp.id,nbs.slug,shp.action,shp.area"
           " from waterproof_nbs_ca_waterproofnbsca nbs"
           " join waterproof_nbs_ca_activityshapefile shp on nbs.activity_shapefile_id = shp.id"
           " where nbs.id=ANY("+sqlParam+");")

    print(sql)

# layer = conn.GetLayerByName("delineated_catchment")
    layer = conn.ExecuteSQL(sql)

    feat = layer.GetNextFeature()
    n=0
    outputList=[]
    if feat is None:
        sqlParam2=str(nbs[0])
        sql2 = ("select shp.id,nbs.slug,shp.action,shp.area from waterproof_nbs_ca_waterproofnbsca nbs join waterproof_pr_default_nbs shp on shp.id=6 and nbs.id="+sqlParam2+";")
        print(sql2)
        layer2 = conn.ExecuteSQL(sql2)
        feat2 = layer2.GetNextFeature()
        while feat2 is not None:
            output = os.path.join(path, "activity_"+feat2.slug+"_shp")
            print(output)
            source = osr.SpatialReference()        
            source.ImportFromEPSG(4326)
            target = osr.SpatialReference()
            epsg_3857 = 3857
            epsg_54004 = 54004
            target.ImportFromEPSG(epsg_54004)
            transform = osr.CoordinateTransformation(source, target)
            # Schema definition of SHP file
            out_driver = ogr.GetDriverByName('ESRI Shapefile')
            if os.path.exists(output):
                out_driver.DeleteDataSource(output)

            out_ds = out_driver.CreateDataSource(output)

            out_layer = out_ds.CreateLayer("activities", target, ogr.wkbMultiPolygon)
            fd_activity = ogr.FieldDefn('activity_n', ogr.OFTString)
            fd_action = ogr.FieldDefn('action', ogr.OFTString)
            out_layer.CreateField(fd_activity)
            out_layer.CreateField(fd_action)
            # print(feat)
            featDef = ogr.Feature(out_layer.GetLayerDefn())
            geom = feat2.GetGeometryRef()
            geom.Transform(transform)
            featDef.SetGeometry(geom)
            featDef.SetField('activity_n', feat2.slug)
            featDef.SetField('action', feat2.action)
            out_layer.CreateFeature(featDef)
            feat2.Destroy()
            feat2 = layer.GetNextFeature()
            outputList.append(output)
            n=n+1
    else: 
        while feat is not None:
            output = os.path.join(path, "activity_"+feat.slug+"_shp")
            print(output)
            source = osr.SpatialReference()        
            source.ImportFromEPSG(4326)
            target = osr.SpatialReference()
            epsg_3857 = 3857
            epsg_54004 = 54004
            target.ImportFromEPSG(epsg_54004)
            transform = osr.CoordinateTransformation(source, target)
            # Schema definition of SHP file
            out_driver = ogr.GetDriverByName('ESRI Shapefile')
            if os.path.exists(output):
                out_driver.DeleteDataSource(output)

            out_ds = out_driver.CreateDataSource(output)

            out_layer = out_ds.CreateLayer("activities", target, ogr.wkbMultiPolygon)
            fd_activity = ogr.FieldDefn('activity_n', ogr.OFTString)
            fd_action = ogr.FieldDefn('action', ogr.OFTString)
            out_layer.CreateField(fd_activity)
            out_layer.CreateField(fd_action)
            # print(feat)
            featDef = ogr.Feature(out_layer.GetLayerDefn())
            geom = feat.GetGeometryRef()
            geom.Transform(transform)
            featDef.SetGeometry(geom)
            featDef.SetField('activity_n', feat.slug)
            featDef.SetField('action', feat.action)
            out_layer.CreateFeature(featDef)
            feat.Destroy()
            feat = layer.GetNextFeature()
            outputList.append(output)
            n=n+1

    conn.Destroy()
    out_ds.Destroy()
    return outputList


def resamplingRaster(templatePath, srcPath, out):

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
    dst = gdal.GetDriverByName('Gtiff').Create(
        out, wide, high, 1, gdalconst.GDT_Float32)
    dst.SetGeoTransform(match_geotrans)
    dst.SetProjection(match_proj)

    # Do the work
    gdal.ReprojectImage(src, dst, src_proj, match_proj,
                        gdalconst.GRA_NearestNeighbour)

    del dst  # Flush

    print("finish")


# Obtener parametros de modelo
def getParameters(basin, model):
    logger.debug("getParameters")
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_getparametersmodel', [basin, model])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
    cursor.close()
    return listResult

# Recuperar macroregion por id


def getRegionFromId(basin):
    result = ''
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_getbasin', [basin])
    result = cursor.fetchall()
    for row in result:
        result = row
    cursor.close()
    return result

# Recuperar constante por macroregion


def getConstantFromBasin(basin, constantName):
    result = ''
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_getconstant', [basin, constantName])
    result = cursor.fetchall()
    for row in result:
        result = row
    cursor.close()
    return result

# Cortar raster


def cutRaster(catchment, path, out_path):
    data = rasterio.open(path)
    with fiona.open(catchment, "r") as shapefile:
        shapes = [feature["geometry"] for feature in shapefile]

    with rasterio.open(path) as src:
        # if 'Stream' in path or 'Soil_Depth' in path:
        #	nd = 255
        # else:
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

    with rasterio.open(os.path.join(out_path, os.path.basename(path)), "w", **out_meta) as dest:
        dest.write(out_image)

    return os.path.join(out_path, os.path.basename(path))

# Obtener los costos calculados para las NBS de un caso de estudi
def getCurrencyCostCalculated(studyCase,nbsList):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_currency_cost_calculated', [studyCase,nbsList])
    result = cursor.fetchall()
    for row in result:
        # print(row)
        listResult.append(row)
    cursor.close()
    return listResult

# Obtener las actividades asociadas a una SBN

def getActivities(nbsList, user_id):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_activities', [nbsList])
    result = cursor.fetchall()
    for row in result:
        # print(row)
        listResult.append(row)
    cursor.close()
    return listResult

def getNbsBudget(nbsList,id_case):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_nbs_budget', [nbsList,id_case])
    result = cursor.fetchall()
    for row in result:
        # print(row)
        listResult.append(row)
    cursor.close()
    return listResult

# Verificar las transacciones configuradas para una SBN
def checkNbsTransitionMap(idNbs,id_transition):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_check_nbs_transition_map', [idNbs,id_transition])
    result = cursor.fetchall()
    if (len(result)>0):
        cursor.close()
        return True
    else:
        return False


def getNbsTransformations(nbsList):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_nbs_transformations', [nbsList])
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
    cursor.callproc('__wp_gettransitions', [])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
    cursor.close()
    return listResult


def getParametersByObj(id_obj, id_basin):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_getparametersbyobj', [id_basin, id_obj])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
    cursor.close()
    return listResult


def getActivityShapefile(nbsList):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_activities_shapefiles', [nbsList])
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
        cursor.callproc('__wp_getobjectives', [id])
        result = cursor.fetchall()
        for row in result:
            listResult.append(row)
        cursor.close()

    return listResult

def getDefaultTransitionPriority(obj,transition):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_default_transitions_priorities', [obj,transition])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
        cursor.close()

    return listResult

def getUserTransitionPriority(obj,transition,catchment,user,studyCase):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_user_transitions_priorities', [obj,transition,catchment,user,studyCase])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
        cursor.close()

    return listResult

def getUserObjectivePriority(obj,transition,parameter,catchment,user,studyCase):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_user_objectives_priorities', [obj,transition,parameter,catchment,user,studyCase])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
        cursor.close()

    return listResult

def getDefaultObjectivePriority(obj,transition,parameter):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_default_objectives_priorities', [obj,transition,parameter])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
        cursor.close()

    return listResult

def getStudyCaseBudget(id_case):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_studycase_budget', [id_case])
    result = cursor.fetchall()
    for row in result:
        # print(row)
        listResult.append(row)
    cursor.close()
    return listResult

# Procesar parametros
def processParameters(nbsList, parametersList, id_catchment, id_case, basin, pathF, user, objectives, inputs_objs, outPreProc, catchment,pcp_label):
    # def processParameters(parametersList, basin, catchment,pathF, user):
    dictParameters = dict()
    default = 'y'
    out_path = ""
    in_path = ""
    out_folder = parametersList[0][9]
    in_folder='02-PREPROC_RIOS'
    out_path = os.path.join(os.getcwd(), pathF, 'out', out_folder)
    in_path = os.path.join(os.getcwd(), pathF, 'in', out_folder)
    in_preProc=os.path.join(os.getcwd(), pathF, 'in', in_folder)

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
                strNbsList=[]
                listAct = getActivities(nbsList, user)
                for nbs in nbsList:
                    strNbsList.append(str(nbs[0]))
                listActCurrencyCost=getCurrencyCostCalculated(id_case,strNbsList)
                # print(listAct)
                for la in listAct:
                    CImple=filter(lambda x: x[0]==str(la[3]) and x[1]=='unit_implementation_cost',listActCurrencyCost)
                    CImple=CImple[0][2]
                    #COport=la[4]
                    COport=filter(lambda x: x[0]==str(la[3]) and x[1]=='unit_oportunity_cost',listActCurrencyCost)
                    COport=COport[0][2]
                    #CMant=la[2]
                    CMant=filter(lambda x: x[0]==str(la[3]) and x[1]=='unit_maintenance_cost',listActCurrencyCost)
                    CMant=CMant[0][2]
                    FrecMant=la[5]
                    dictParameters[name][remove_accents(la[0])] = {}
                    dictParameters[name][remove_accents(
                        la[0])]["measurement_unit"] = measurement_unit
                    dictParameters[name][remove_accents(
                        la[0])]["measurement_value"] = measurement_value
                    dictParameters[name][remove_accents(la[0])]["unit_cost"] = float(
                        CImple+COport+(CMant/FrecMant))

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
                listPolygons = getActivityShapefile(nbsList)
                outShp = exportToShpActivities(nbsList, in_path, user)
                # listAct.append(outShp)
                #value = listAct
                value = outShp

            elif(riosType == 'transition_map'):
                dictParameters[name] = {}
                transitionsList = getTransitions()
                for transition in transitionsList:
                    dictParameters[name][transition[1]] = {}
                    listActivities = getActivities(nbsList, user)
                    for activity in listActivities:
                        idNbs=activity[3]
                        transition_map=checkNbsTransitionMap(idNbs,transition[3])
                        name_ = remove_accents(activity[0])
                        if (transition_map):
                            dictParameters[name][transition[1]][name_] = 1
                        else:
                            dictParameters[name][transition[1]][name_] = 0
                value = dictParameters[name]

            elif(riosType == 'lulc_act'):
                key_lulc = "lulc_coefficients_table_uri"
                dictParameters[name] = {}
                file = ""
                listActivities_1 = getActivities(nbsList, user)
                transformations = getNbsTransformations(nbsList)

                if(key_lulc not in dictParameters):
                    # print("no existe no")
                    region = getRegionFromId(basin)
                    label = region[4]
                    file = os.path.join(os.getcwd(), pathF,
                                        'in', "biophysical_table.csv")
                    #values,headers = getColsParams("apps.skaphe.com",27017,"waterProof","parametros_biofisicos",user,label,True)
                    values, headers = getDefaultBiophysicParams(label, default)
                    valuesUser, headersUser = getUserBiophysicParams(
                        id_catchment, id_case, user, label, 'N')
                    # Reemplazar los parametros del usuario
                    # en los parametros por defecto
                    for userIdx, valUser in enumerate(valuesUser):
                        for defIdx, defVal in enumerate(values):
                            if (valUser[0] == defVal[0]):
                                values[defIdx] = valUser
                    generateCsv(headers, values, file)
                    value = file

                listCsv = filterCsvLucode(file, "lucode")

                for lulc in listCsv:
                    dictParameters[name][lulc] = []
                    for trans in transformations:
                        if (lulc == str(trans[0])):
                            list_la = []
                            list_la.append(remove_accents(trans[4]))
                            dictParameters[name][lulc].append(list_la[0])
                    # print(listActivities_1)
                    # for act in listActivities_1:
                    #     list_la.append(remove_accents(act[0]))

                    # print(list_la)

                value = dictParameters[name]

            elif(riosType == "priorities"):
                dictParameters[name] = {}
                transitionsList = getTransitions()
                for transition in transitionsList:
                    dictParameters[name][transition[1]] = {}
                    listObjectives = getObjectives(objectives)
                    for obj in listObjectives:
                        user_priority=getUserTransitionPriority(obj[1],transition[5],int(id_catchment),int(user),int(id_case))
                        if (len(user_priority)>0):
                            for value in user_priority:
                                replacedDotValue=value[0].replace(',','.')
                                dictParameters[name][transition[1]][obj[0]] = float(replacedDotValue)
                        else:
                            default_priority=getDefaultTransitionPriority(obj[1],transition[5])
                            for value in default_priority:
                                replacedDotValue=value[0].replace(',','.')
                                dictParameters[name][transition[1]][obj[0]] = float(replacedDotValue)

                value = dictParameters[name]
                # print(listCsv)

            elif(riosType == "budget_conf"):
                # Consultar datos basicos del budget para el caso de estudio 
                studyCase_budget=getStudyCaseBudget(id_case)
                years_spend=studyCase_budget[0][1]
                report_rem=studyCase_budget[0][3]
                anual_investment=studyCase_budget[0][2]
                analysis_type=studyCase_budget[0][0]
                #  public.waterproof_study_cases_studycases campo analysys_type para saber si es full o investment
                dictParameters[name] = {}
                # Parametro a sustituir por el numero de años
                dictParameters[name]["years_to_spend"] =  years_spend
                #public.waterproof_study_cases_studycases.reminder True|False 
                # Si es True colocar "Proportional reallocate"
                # Si es false "Report remainder"
                if (report_rem==True):
                    dictParameters[name]["if_left_over"] = "Proportional reallocate" 
                else:
                    dictParameters[name]["if_left_over"] = "Report remainder" 

                dictParameters[name]["activity_budget"] = {}
                listAct = getNbsBudget(nbsList, id_case)
                #Validar si el tipo analisis: Full|Investment
                if (analysis_type=='FULL'):
                    print("FULL")
                    print(listAct)
                    for la in listAct:
                        name_ = remove_accents(la[0])
                        dictParameters[name]["activity_budget"][name_] = {}
                        budget_amount=float(la[6])*999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999
                        # Si es investment se consulta public.waterproof_study_cases_studycases_nbs.value
                        # Si es Full se consulta public.waterproof_study_cases_studycases_nbs.value pero es porcentaje y se calcula sobre el floating_budget
                        dictParameters[name]["activity_budget"][name_]["budget_amount"] = budget_amount  # TODO
                        # Sustituir
                        # Si es de tipo full va el 9999999
                        # Si es investment va el valor que diga el campo public.waterproof_study_cases_studycases.anual_investment
                        dictParameters[name]["floating_budget"] = 999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999 
                elif(analysis_type=='INVESTMENT'):
                    print("INVESTMENT")
                    for la in listAct:
                        name_ = remove_accents(la[0])
                        dictParameters[name]["activity_budget"][name_] = {}
                        # Si es investment se consulta public.waterproof_study_cases_studycases_nbs.value
                        # Si es Full se consulta public.waterproof_study_cases_studycases_nbs.value pero es porcentaje y se calcula sobre el floating_budget
                        dictParameters[name]["activity_budget"][name_]["budget_amount"] = float(la[6])  # TODO
                        dictParameters[name]["floating_budget"] = float(anual_investment)

                value = dictParameters[name]

            elif(riosType == "objectives"):
                dictParameters[name] = {}
                listObjectives = getObjectives(objectives)
                for obj in listObjectives:
                    dictParameters[name][obj[0]] = {}
                    dictParameters[name][obj[0]
                                         ]["rios_model_type"] = "rios_tier_0" 
                    dictParameters[name][obj[0]]["priorities"] = {}
                    transitionsList = getTransitions()
                    listParametersObj = getParametersByObj(obj[1], basin)
                    for transition in transitionsList:
                        dictParameters[name][obj[0]
                                             ]["priorities"][transition[1]] = {}
                        for param in listParametersObj:
                            user_priority=getUserObjectivePriority(obj[1],transition[5],param[3],int(id_catchment),int(user),int(id_case))
                            if (len(user_priority)>0):
                                for value in user_priority:
                                    if (',' in value[0]):
                                        replacedDotValue=value[0].replace(',','.')
                                        dictParameters[name][obj[0]]["priorities"][transition[1]][param[0]] = replacedDotValue
                                    else:
                                        dictParameters[name][obj[0]]["priorities"][transition[1]][param[0]] = value[0]
                            else:
                                default_priority=getDefaultObjectivePriority(obj[1],transition[5],param[3])
                                for value in default_priority:
                                    if (',' in value[0]):
                                        replacedDotValue=value[0].replace(',','.')
                                        dictParameters[name][obj[0]]["priorities"][transition[1]][param[0]] = replacedDotValue
                                    else:
                                        dictParameters[name][obj[0]]["priorities"][transition[1]][param[0]] = value[0]
                            
                            # dictParameters[name][obj[0]]["priorities"][transition[1]][param[0]] = '~0.25'

                    dictParameters[name][obj[0]]["factors"] = {}

                    for param in listParametersObj:
                        region = getRegionFromId(basin)
                        label = region[4]
                        if(param[0] == 'Vegetative Cover Index' or param[0] == 'Land Use Land Cover Retention at pixel'
                           or param[0] == 'On-pixel retention' or param[0] == 'On-pixel source'):
                            ranks = {
                                'Vegetative Cover Index': 'Cover_Rank',
                                'Land Use Land Cover Retention at pixel': 'Rough_Rank',
                                'On-pixel retention': 'Sed_Ret',
                                'On-pixel source': 'Sed_Exp'
                            }

                            file = os.path.join(
                                os.getcwd(), pathF, 'in', "biophysical_table.csv")
                            #values,headers = getColsParams("apps.skaphe.com",27017,"waterProof","parametros_biofisicos",user,label,True)
                            values, headers = getDefaultBiophysicParams(
                                label, default)
                            valuesUser, headersUser = getUserBiophysicParams(
                                id_catchment, id_case, user, label, 'N')
                            # Reemplazar los parametros del usuario
                            # en los parametros por defecto
                            for userIdx, valUser in enumerate(valuesUser):
                                for defIdx, defVal in enumerate(values):
                                    if (valUser[0] == defVal[0]):
                                        values[defIdx] = valUser
                            generateCsv(headers, values, file)
                            # value = file
                            dictParameters[name][obj[0]
                                                 ]["factors"][param[0]] = {}
                            dictParameters[name][obj[0]
                                                 ]["factors"][param[0]]["bins"] = {}
                            dictParameters[name][obj[0]]["factors"][param[0]
                                                                    ]["bins"]["key_field"] = 'lulc_general'
                            dictParameters[name][obj[0]]["factors"][param[0]
                                                                    ]["bins"]["raster_uri"] = param[2]
                            dictParameters[name][obj[0]
                                                 ]["factors"][param[0]]["bins"]["uri"] = file
                            dictParameters[name][obj[0]]["factors"][param[0]
                                                                    ]["bins"]["value_field"] = ranks[param[0]]
                        else:
                            if inputs_objs[objectives_mapping[obj[0]]].has_key(param[0]):
                                dictParameters[name][obj[0]
                                                     ]["factors"][param[0]] = {}
                                if (param[0]=='Rainfall depth'):
                                    dictParameters[name][obj[0]]["factors"][param[0]]["raster_uri"] = os.path.join(
                                    in_preProc, inputs_objs[objectives_mapping[obj[0]]][param[0]].format(label,pcp_label))
                                else:
                                    dictParameters[name][obj[0]]["factors"][param[0]]["raster_uri"] = os.path.join(
                                    outPreProc, inputs_objs[objectives_mapping[obj[0]]][param[0]].format(label,pcp_label))
                                dictParameters[name][obj[0]
                                                     ]["factors"][param[0]]["bins"] = {}
                                dictParameters[name][obj[0]]["factors"][param[0]
                                                                        ]["bins"]["inverted"] = False
                                dictParameters[name][obj[0]]["factors"][param[0]
                                                                        ]["bins"]["type"] = "interpolated"
                                dictParameters[name][obj[0]]["factors"][param[0]
                                                                        ]["bins"]["interpolation"] = "linear"
                            else:
                                # print(objectives_mapping[obj[0]])
                                # print(inputs_objs)
                                dictParameters[name][obj[0]
                                                     ]["factors"][param[0]] = {}
                                dictParameters[name][obj[0]]["factors"][param[0]
                                                                        ]["raster_uri"] = param[2]
                                dictParameters[name][obj[0]
                                                     ]["factors"][param[0]]["bins"] = {}
                                dictParameters[name][obj[0]]["factors"][param[0]
                                                                        ]["bins"]["inverted"] = False
                                dictParameters[name][obj[0]]["factors"][param[0]
                                                                        ]["bins"]["type"] = "interpolated"
                                dictParameters[name][obj[0]]["factors"][param[0]
                                                                        ]["bins"]["interpolation"] = "linear"

                value = dictParameters[name]

        if(outPathType):
            value = out_path

        if(bio_param):
            # print("bio_param: " + name)
            region = getRegionFromId(basin)
            label = region[4]
            file = os.path.join(os.getcwd(), pathF, 'in',
                                "biophysical_table.csv")
            #values,headers = getColsParams("apps.skaphe.com",27017,"waterProof","parametros_biofisicos",user,label,True)
            values, headers = getDefaultBiophysicParams(label, default)
            valuesUser, headersUser = getUserBiophysicParams(
                id_catchment, id_case, user, label, 'N')
            # Reemplazar los parametros del usuario
            # en los parametros por defecto
            for userIdx, valUser in enumerate(valuesUser):
                for defIdx, defVal in enumerate(values):
                    if (valUser[0] == defVal[0]):
                        values[defIdx] = valUser
            generateCsv(headers, values, file)
            value = file

        if(cut):
            value = cutRaster(catchment, value, in_path)

        dictParameters[name] = value

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

        return dictParameters, out_path


def executeFunction(basin, id_catchment, id_usuario, inputs):
    date = datetime.date.today()
    path = os.path.join("/home/skaphe/Documentos/tnc/modelos/Workspace_BasinDelineation/tmp",
                        str(id_usuario) + "_" + str(date.year) + "_" + str(date.month) + "_" + str(date.day))
    pathPreprocIn = os.path.join(path, "in", "02-PREPROC_RIOS")
    pathPreprocOut = os.path.join(path, "out", "02-PREPROC_RIOS")
    pathCatchment = os.path.join(path, "in", "catchment")

    isdir = os.path.isdir(path)
    if(not isdir):
        os.mkdir(path)
        os.mkdir(os.path.join(path, "in"))
        os.mkdir(os.path.join(path, "out"))

    isdir = os.path.isdir(os.path.join(path, "in"))
    if(not isdir):
        os.mkdir(os.path.join(path, "in"))

    isdir = os.path.isdir(os.path.join(path, "out"))
    if(not isdir):
        os.mkdir(os.path.join(path, "out"))

    isdir = os.path.isdir(pathPreprocIn)
    if(not isdir):
        os.mkdir(pathPreprocIn)

    isdir = os.path.isdir(pathPreprocOut)
    if(not isdir):
        os.mkdir(pathPreprocOut)

    isdir = os.path.isdir(pathCatchment)
    if(not isdir):
        os.mkdir(pathCatchment)

    list = getParameters(basin, 'preprocRIOS')
    catchment = exec_preproc.exportToShp(id_catchment, path, False)
    parameters, out_path = processParameters(
        list, basin, catchment, path, inputs, id_usuario)

    #print(parameters)
    print ("save file :: %s%s" % (out_path,"parameters_rios.json"))
    txt_file = open(os.path.join(out_path,"parameters_rios.json"), "w")
    json_parameters = json.dumps(parameters, indent=2)
    txt_file.write(json_parameters)
    txt_file.close()

    Pro.main(working_path=parameters["working_path"],
             output_path=parameters["output_path"],
             hydro_path=parameters["hydro_path"],
             rios_coeff_table=parameters["rios_coeff_table"],
             lulc_raster_uri=parameters["lulc_raster_uri"],
             dem_raster_uri=parameters["dem_raster_uri"],
             erosivity_raster_uri=parameters["erosivity_raster_uri"],
             erodibility_raster_uri=parameters["erodibility_raster_uri"],
             soil_depth_raster_uri=parameters["soil_depth_raster_uri"],
             precip_month_raster_uri=parameters["precip_month_raster_uri"],
             soil_texture_raster_uri=parameters["soil_texture_raster_uri"],
             precip_annual_raster_uri=parameters["precip_annual_raster_uri"],
             aet_raster_uri=parameters["aet_raster_uri"],
             suffix=parameters["suffix"],
             aoi_shape_uri=parameters["aoi_shape_uri"],
             streams_raster_uri=parameters["streams_raster_uri"],
             # Objetivo de aporte de sedimentos para reservorios y sistemas de tratamiento
             do_erosion=parameters["do_erosion"],
             # Objetivo nutrientes Fosforo
             do_nutrient_p=parameters["do_nutrient_p"],
             # Objetivo nutrientes Nitrogeno
             do_nutrient_n=parameters["do_nutrient_n"],
             # Objetivo control de inundaciones
             do_flood=parameters["do_flood"],
             # Objetivo recarga de agua subterranea y flujo base
             do_gw_bf=parameters["do_gw_bf"],
             river_buffer_dist=int(parameters["river_buffer_dist"]))  # Buffer


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
    # logger.debug("execModel :: args :: %s", args)
    # print(args)
    rios.execute(args)

