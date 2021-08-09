# Date: 27/10/2020
# Author: Diego Rodriguez - Skaphe Tecnologia SAS
# WFApp

import sys
import os
sys.path.append('config')
sys.path.append(os.path.split(os.getcwd())[0] + os.path.sep + 'RIOS_Toolbox')
import logging
import RIOS_Toolbox.rios_preprocessor as Pro
from connect import connect
from config import config
import rasterio
import fiona
import ogr
import osr
import datetime
import json
import AdvancedHTMLParser 
from AdvancedHTMLParser import AdvancedTag
from rasterio.mask import mask
from zonalStatistics import calculateRainfallDayMonth, calculateStatistic
from createBioParamCsv import getColsParams, generateCsv, getDefaultBiophysicParams,getUserBiophysicParams

ruta = os.environ["PATH_FILES"]

objectivesDict = {
    'do_erosion': {
        'Downslope retention index': 'erosion_downslope_retention_index_{0}.tif',
        'Upslope source': 'erosion_upslope_source_{0}.tif',
        'Riparian continuity': 'erosion_riparian_index_{0}.tif'
    },
    'do_nutrient_p': {
        'Downslope retention index': 'phosphorus_downslope_retention_index_{0}.tif',
        'Upslope source': 'phosphorus_upslope_source_{0}.tif',
        'Riparian continuity': 'phosphorus_riparian_index_{0}.tif'
    },
    'do_nutrient_n': {
        'Downslope retention index': 'nitrogen_downslope_retention_index_{0}.tif',
        'Upslope source': 'nitrogen_upslope_source_{0}.tif',
        'Riparian continuity': 'nitrogen_riparian_index_{0}.tif'
    },
    'do_flood': {
        'Downslope retention index': 'flood_downslope_retention_index_{0}.tif',
        'Upslope source': 'flood_upslope_source_{0}.tif',
        'Slope Index': 'flood_slope_index_{0}.tif',
        'Riparian continuity': 'flood_riparian_index_{0}.tif',
        'Rainfall depth':'Pcp_{0}_{1}.tif'
    },
    'do_gw_bf': {
        'Downslope retention index': 'erosion_downslope_retention_index_{0}.tif',
        'Upslope source': 'gwater_upslope_source_{0}.tif',
        'Slope Index': 'flood_slope_index_{0}.tif'
    }
}
logger = logging.getLogger('exec_preproc')
logger.setLevel(logging.DEBUG)
# Exportar cuenca delimitada a shp


def exportToShp(catchment, path):
    params = config(section='postgresql_alfa')
    connString = "PG: host=" + params['host'] + " dbname=" + params['database'] + \
        " user=" + params['user'] + " password=" + params['password']
    conn = ogr.Open(connString)
    if conn is None:
        print('Could not open a database or GDAL is not correctly installed!')
        sys.exit(1)

    output = os.path.join(path, "in", "catchment", "catchment.shp")
    source = osr.SpatialReference()
    source.ImportFromEPSG(4326)
    target = osr.SpatialReference()
    epsg_3857 = 3857
    epsg_54004 = 54004
    target.ImportFromEPSG(epsg_54004)
    transform = osr.CoordinateTransformation(source, target)

    # Schema definition of SHP file
    out_driver = ogr.GetDriverByName('ESRI Shapefile')
    out_ds = out_driver.CreateDataSource(output)

    out_layer = out_ds.CreateLayer("catchment", target, ogr.wkbPolygon)
    fd = ogr.FieldDefn('ws_id', ogr.OFTInteger)
    fd1 = ogr.FieldDefn('subws_id', ogr.OFTInteger)
    out_layer.CreateField(fd)
    out_layer.CreateField(fd1)
    params = ' = ' + catchment
    # if(len(catchment) == 1):
    #     print("LENTCH:::")
    #     params = ' = ' + str(catchment[0])
    # elif(len(catchment) > 1):
    #     params = ' IN ('
    #     for c in catchment:
    #         params = params + str(c) + ','
    #     params = params[:-1] + ')'
    #     print(":::PARAMS:::")
    #     print(params)

    if (catchment != -1):
        sql = "select * from waterproof_intake_polygon where delimitation_type = 'SBN' and intake_id" + \
            str(params)
        print(":::SQL:::")
        print(sql)
        # layer = conn.GetLayerByName("delineated_catchment")
        layer = conn.ExecuteSQL(sql)
        count = layer.GetFeatureCount()

        if(count == 0):
            sql = "select * from waterproof_intake_polygon where delimitation_type = 'CATCHMENT' and intake_id" + \
                str(params)
            layer = conn.ExecuteSQL(sql)

        feat = layer.GetNextFeature()

        while feat is not None:
            featDef = ogr.Feature(out_layer.GetLayerDefn())
            geom = feat.GetGeometryRef()
            geom.Transform(transform)
            featDef.SetGeometry(geom)
            featDef.SetField('ws_id', feat.id)
            featDef.SetField('subws_id', feat.id)
            out_layer.CreateFeature(featDef)
            feat.Destroy()
            feat = layer.GetNextFeature()

    conn.Destroy()
    out_ds.Destroy()

    return os.path.join(os.getcwd(), output)


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

def getStudyCasePtaps(studycase_id):
    conn = connect('postgresql_alfa')
    cursor = conn.cursor()
    sql = "select header_id from public.waterproof_study_cases_studycases_ptaps where studycases_id = %s" % studycase_id
    cursor.execute(sql)
    result = cursor.fetchall()    
    cursor.close()
    return result

def getStudyCaseObjectives(id_case):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_studycase_objective', [id_case])
    result = cursor.fetchall()
    for row in result:
        # print(row)
        listResult.append(row)
    cursor.close()
    return listResult

# Obtener captaciones asociadas a una PTAP 

def getPtapCatchmentsByStudyCase(caseStudy):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_ptap_catchments_by_studycase', [caseStudy])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
    return listResult

# Obtener captaciones asociadas a un caso de estudio


def getStudyCaseCatchments(caseStudy):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_studyCase_catchments', [caseStudy])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
    return listResult

# Obtener captaciones asociadas a un caso de estudio


def getCatchmentBasin(catchment):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_catchment_basin', [catchment])
    result = cursor.fetchall()
    for row in result:
        print("Row basin")
        print(row[0])
        listResult.append(row[0])
    return listResult


# Obtener NBS asociadas al caso de estudio

def getStudyCaseNbs(caseStudy):
    result = ''
    listResult = []
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('__wp_get_studycase_nbs', [caseStudy])
    result = cursor.fetchall()
    for row in result:
        listResult.append(row)
    return listResult

# Obtener parametros de modelo

def getParameters(basin, model):
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


def cutRaster(catchment, path, out_path, cut_raster_name):
    data = rasterio.open(path)
    with fiona.open(catchment, "r") as shapefile:
        shapes = [feature["geometry"] for feature in shapefile]

    with rasterio.open(path) as src:
        nd = -999
        if 'Stream' in path or 'Soil_Depth' in path or 'int' in src.dtypes[0]:
            nd = 255
        

        out_image, out_transform = mask(src, shapes, crop=True, nodata=nd)
        out_meta = src.meta

    print(path)

    out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform,
                     "nodata": nd})

    if (cut_raster_name == ''):
        cut_raster_name = os.path.basename(path)
    with rasterio.open(os.path.join(out_path, cut_raster_name), "w", **out_meta) as dest:
        dest.write(out_image)

    return os.path.join(out_path, cut_raster_name)

# Procesar parametros


def processParameters(parametersList, basin,id_catchment, studyCase,catchment, pathF, inputs, user):
    dictParameters = dict()
    out_path = ""
    in_path = ""
    out_folder = parametersList[0][9]
    out_path = os.path.join(os.getcwd(), pathF, 'out', out_folder)
    in_path = os.path.join(os.getcwd(), pathF, 'in', out_folder)
    catchment_out = ""
    logger.debug("processParameters :: start")

    isdir = os.path.isdir(out_path)
    if(not isdir):
        os.mkdir(out_path)

    isdir = os.path.isdir(in_path)
    if(not isdir):
        os.mkdir(in_path)

    # print(parametersList)

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

        if(suffix):
            region = getRegionFromId(basin)
            label = region[4]
            value = label
        if(constant):
            constantValue = getConstantFromBasin(basin, name)
            value = constantValue[2]
        if(empty):
            value = ''
        if(cut):
            
            cut_raster_name = os.path.basename(value)
            if ('LandCoverResampling' in value):
                analysis_period = analysisPeriodFromStudyCase(studyCase)
                value_last_year = value.replace('Resampling', '/YEAR_%s' %(analysis_period))
                cut_raster_name_future = cut_raster_name.replace('.tif', '_FUTURE.tif')
                cutRaster(catchment, value_last_year, in_path, cut_raster_name_future)

            value = cutRaster(catchment, value, in_path, cut_raster_name)
            catchment_out = catchment
        if(file):
            value = catchment
        if(outPathType):
            value = out_path
        if(calculado):
            region = getRegionFromId(basin)
            label = region[4]
            maxMonth, outRaster = calculateRainfallDayMonth(
                value, catchment, label)
            value = cutRaster(catchment, outRaster, in_path,os.path.basename(outRaster))
        if(inputUser):
            value = inputs[name]
        if(bio_param):
            region = getRegionFromId(basin)
            label = region[4]
            default = 'y'
            file = os.path.join(os.getcwd(), pathF, 'in',
                                "biophysical_table.csv")
            # values, headers = getColsParams(
            #     "apps.skaphe.com", 27017, "waterProof", "parametros_biofisicos", user, label, True)
            values,headers=getDefaultBiophysicParams(label,default)
            valuesUser,headersUser=getUserBiophysicParams(id_catchment,studyCase,user,label,'N')
            # Reemplazar los parametros del usuario 
            # en los parametros por defecto
            for userIdx,valUser in enumerate(valuesUser):
                for defIdx,defVal in enumerate(values):
                    if (valUser[0]==defVal[0]):
                        values[defIdx]=valUser
            generateCsv(headers, values, file)
            value = file
        dictParameters[name] = value
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

        return dictParameters, out_path, catchment_out,maxMonth


def executeFunction(basin, id_catchment, id_usuario, inputs,id_case,catchmentDir):
    today = datetime.date.today()
    # path = os.path.join("/home/skaphe/Documentos/tnc/modelos/Workspace_BasinDelineation/tmp",str(id_usuario) +  "_" + str(date.year) + "_" + str(date.month) + "_" + str(date.day))
    # path = os.path.join("data","wpdev","salidas",str(id_usuario) +  "_" + str(date.year) + "_" + str(date.month) + "_" + str(date.day))
    path = os.path.join(ruta, "salidas", "%s_%s_%s-%s-%s" % (int(id_usuario), int(id_case), today.year, today.month, today.day))
    pathPreprocIn = os.path.join(path,catchmentDir, "in", "02-PREPROC_RIOS")
    pathPreprocOut = os.path.join(path,catchmentDir, "out", "02-PREPROC_RIOS")
    pathCatchment = os.path.join(path,catchmentDir, "in", "catchment")

    #print(inputs)

    isdir = os.path.isdir(path)
    if(not isdir):
        os.mkdir(path)
    isdir = os.path.isdir(os.path.join(path, catchmentDir))
    if(not isdir):
        os.mkdir(os.path.join(path, catchmentDir))
        os.mkdir(os.path.join(path,catchmentDir, "in"))
        os.mkdir(os.path.join(path, catchmentDir,"out"))

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
    path = os.path.join(path,catchmentDir)
    catchment = exportToShp(id_catchment, path)
    parameters, out_path, catchmentOut,pcp_label = processParameters(
        list, basin,id_catchment,id_case, catchment, path, inputs, id_usuario,)

    logger.debug("parameters :: %s", parameters)

    objectives = {}

    for i in inputs:
        objectives[i] = objectivesDict[i]

    with (open(out_path + '_preprocessor_parameters.json', 'w')) as fp:
        json.dump(parameters, fp)
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

    return objectives, parameters["output_path"], catchmentOut,pcp_label

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

def analysisPeriodFromStudyCase(id):
	print("analysisPeriodFromStudyCase - id::%s" % id)
	conn = connect('postgresql_alfa')
	cursor = conn.cursor()
	sql = "select analysis_period_value from public.waterproof_study_cases_studycases where id = %s" % id
	cursor.execute(sql)
	year = 1
	try:
		row = cursor.fetchone()
		year = row[0]
	except:
		year=-1
	return year

""" Function to get All Years budget from IPA Report(Rios Portfolio)"""
""" using AdvancedHTMLParser return all the elements with className = budget_year """
def parse_to_get_ipa_report(path_file,catchment,id_case,id_usuario):

    path_file=path_file+"/1_investment_portfolio_adviser_workspace/html_report/ipa_report.html"
    class_name = "budget_year"
    f = open(path_file, 'r')
    html = f.read()
    parser = AdvancedHTMLParser.AdvancedHTMLParser()
    parser.parseStr(html)
    budget_years = parser.getElementsByClassName(class_name)
    conn = connect('postgresql_alfa')
    cursor = conn.cursor()
    today = datetime.date.today()
    date=str(today.year)+'-'+str(today.month)+'-'+str(today.day)
    allYear_quant=len(budget_years[2].children[1].children)-1
    allYear_counter=1
    year=9999
    #-------------------------
    # All Years budget totals
    #------------------------
    while allYear_counter<=allYear_quant:
        allYear_values=budget_years[2].children[1].children[allYear_counter].children
        # FLoating budget
        if (allYear_counter==1):
            sbn=str(allYear_values[0].innerText)
            actual_spent=0
            total_budget=float(allYear_values[2].innerText)
            area_converted=0
            cursor.callproc('__wp_insert_rios_report', [year,sbn,actual_spent,total_budget,area_converted,date,int(catchment),int(id_case),int(id_usuario)]) 
            conn.commit()
        # Activity values
        else:
            sbn=str(allYear_values[0].innerText)
            if (sbn.find('(')>0):
                sbn_split=sbn.split(' ')
                sbn=sbn_split[0]
            actual_spent=float(allYear_values[1].innerText)
            total_budget=float(allYear_values[2].innerText)
            area_converted=float(allYear_values[3].innerText)
            cursor.callproc('__wp_insert_rios_report', [year,sbn,actual_spent,total_budget,area_converted,date,int(catchment),int(id_case),int(id_usuario)]) 
            conn.commit()
        allYear_counter=allYear_counter+1
    years_quant=len(budget_years)-1
    counter=1
    #-----------------
    # Each Year Budget
    #------------------
    while counter<=years_quant:
        ipa_year='ipa_year_'+str(counter)
        budget_year_tag=parser.getElementById(ipa_year)
        budget_year_values=budget_year_tag.children[1].children
        budget_year_quant=len(budget_year_values)-1
        year_counter=1
        while year_counter<=budget_year_quant:
            # Floating budget values
            if (year_counter==1):
                year=counter
                sbn=str(budget_year_values[year_counter].children[0].innerText)
                actual_spent=0
                total_budget=float(budget_year_values[year_counter].children[2].innerText)
                area_converted=0
                cursor = conn.cursor()
                cursor.callproc('__wp_insert_rios_report', [year,sbn,actual_spent,total_budget,area_converted,date,int(catchment),int(id_case),int(id_usuario)]) 
                conn.commit()
            # Activities values
            else:
                year=counter
                sbn=str(budget_year_values[year_counter].children[0].innerText)
                if (sbn.find('(')>0):
                    sbn_split=sbn.split(' ')
                    sbn=sbn_split[0]
                actual_spent=float(budget_year_values[year_counter].children[1].innerText)
                total_budget=float(budget_year_values[year_counter].children[2].innerText)
                area_converted=float(budget_year_values[year_counter].children[3].innerText)
                cursor = conn.cursor()
                cursor.callproc('__wp_insert_rios_report', [year,sbn,actual_spent,total_budget,area_converted,date,int(catchment),int(id_case),int(id_usuario)]) 
                conn.commit()
            year_counter=year_counter+1
        counter=counter+1
    f.close()
    cursor.close()
    conn.close()
    return "Ipa Report Ready"


def updateStudyCaseRunAnalisys(id):
    conn = connect('postgresql_alfa')
    cursor = conn.cursor()
    print ("StudyCase : %s"  % id)
    sql = 'UPDATE waterproof_study_cases_studycases SET is_run_analysis = true WHERE id = %s' % id
    print (sql)
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()

def queryStudyCaseRunAnalisys(id):
    conn = connect('postgresql_alfa')
    cursor = conn.cursor()
    print ("StudyCase : %s"  % id)
    sql = 'SELECT is_run_analysis from waterproof_study_cases_studycases WHERE id = %s' % id
    print (sql)
    cursor.execute(sql)    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result