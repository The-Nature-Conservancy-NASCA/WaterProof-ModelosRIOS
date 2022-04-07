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
import smtplib, ssl
import sys
import requests
import numpy as np
import glob
import ms_templates.templates as ms_templates
import execRIOS 

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from AdvancedHTMLParser import AdvancedTag
from rasterio.mask import mask
from rasterstats import zonal_stats

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

def exportToShp(catchment, path, use_geom_json_field):
    logger.debug("*** init :: exportToShp ***")
    logger.debug("catchment: %s" % catchment)
    logger.debug("path: %s" % path)
    logger.debug("use_geom_json_field: %s" % use_geom_json_field)

    params = config(section='postgresql_alfa')
    connString = "PG: host=" + params['host'] + " dbname=" + params['database'] + \
        " user=" + params['user'] + " password=" + params['password']

    output = os.path.join(path, "in", "catchment", "catchment.shp")
    if use_geom_json_field == False:
        conn = ogr.Open(connString)
        if conn is None:
            print('Could not open a database or GDAL is not correctly installed!')
            sys.exit(1)
    else:
        conn = connect('postgresql_alfa')
        cursor = conn.cursor()
        output = path.replace(".shp", "_using_json.shp")
    
    source = osr.SpatialReference()
    source.ImportFromEPSG(4326)
    target = osr.SpatialReference()    
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

    if (catchment != -1):
        
        if use_geom_json_field == False:
            sql = "select * from waterproof_intake_polygon where delimitation_type in ('SBN','CATCHMENT') and intake_id %s " % params
            print(":::SQL::: %s" % sql)
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
        else:
            sql = 'select id, "geomIntake" from waterproof_intake_polygon where intake_id %s ' % params
            print(":::SQL::: %s" % sql)
            cursor.execute(sql)
            try:
                row = cursor.fetchone()
                feat_coll = row[1] # data as json
                id = row[0]
                geom_intake = json.loads(feat_coll)['features'][0]['geometry']
                geom = ogr.CreateGeometryFromJson(json.dumps(geom_intake))
                featDef = ogr.Feature(out_layer.GetLayerDefn())
                geom.Transform(transform)		
                featDef.SetGeometry(geom)			
                featDef.SetField('ws_id',id)		
                featDef.SetField('subws_id',id)		
                out_layer.CreateFeature(featDef)                
            except:
                print ("No data found")
            out_ds.Destroy()

    logger.debug("*** FINISH :: exportToShp ***")
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
    logger.debug("INIT :: processParameters")
    dictParameters = dict()
    out_path = ""
    in_path = ""
    out_folder = parametersList[0][9]
    out_path = os.path.join(os.getcwd(), pathF, 'out', out_folder)
    in_path = os.path.join(os.getcwd(), pathF, 'in', out_folder)
    catchment_out = ""

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
    
    correct_stream(in_path)

    logger.debug("processParameters :: end")    
    return dictParameters, out_path, catchment_out,maxMonth

def executeFunction(basin, id_catchment, id_usuario, inputs,id_case,catchmentDir):
    today = datetime.date.today()
    path = os.path.join(ruta, "salidas", "%s_%s_%s-%s-%s" % (int(id_usuario), int(id_case), today.year, today.month, today.day))
    pathPreprocIn = os.path.join(path,catchmentDir, "in", "02-PREPROC_RIOS")
    pathPreprocOut = os.path.join(path,catchmentDir, "out", "02-PREPROC_RIOS")
    pathCatchment = os.path.join(path,catchmentDir, "in", "catchment")
    
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
   
    list_param_basin = execRIOS.getParameters(basin, 'preprocRIOS')
    path = os.path.join(path,catchmentDir)
    catchment = exportToShp(id_catchment, path, False)

    logger.debug("executeFunction :: processParameters")
    parameters, out_path, catchmentOut,pcp_label = processParameters(
        list_param_basin, basin,id_catchment,id_case, catchment, path, inputs, id_usuario,)

    logger.debug("parameters :: %s", parameters)

    objectives = {}

    for i in inputs:
        objectives[i] = objectivesDict[i]

    with (open(out_path + '_preprocessor_parameters.json', 'w')) as fp:
        json.dump(parameters, fp)
    logger.debug("Pro.main :: START")
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

    logger.debug("Pro.main :: END")
    print ("finish ::: executeFunction")
    return objectives, parameters["output_path"], catchmentOut,pcp_label

def analysisPeriodFromStudyCase(id):
    logger.debug("analysisPeriodFromStudyCase - id::%s" % id)
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

    logger.debug("END :: analysisPeriodFromStudyCase - year::%s" % year)
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
    allYear_quant=len(budget_years[1].children[1].children)-1
    allYear_counter=1
    year=9999
    #-------------------------
    # All Years budget totals
    #------------------------
    while allYear_counter<=allYear_quant:
        allYear_values=budget_years[1].children[1].children[allYear_counter].children
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

def sendEmail(id_user, study_case_id, start):
    logger.debug("START :: sendEmail")

    sql = "select email, language, first_name  || ' ' || last_name as name from people_profile pp where id = %s" % id_user
    email = 'edwin.piragauta@gmail.com'
    language = 'en'
    user_full_name = email
    study_case_name = 'No Name Study Case'
    result = [email, language, user_full_name]
    try:
        conn = connect('postgresql_alfa')
        cursor = conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchone()    
        cursor.close()
        sql = "select name from waterproof_study_cases_studycases wscs where id = %s " % study_case_id
        cursor = conn.cursor()
        cursor.execute(sql)
        result_sc = cursor.fetchone()
        study_case_name = result_sc[0]
        study_case_name = study_case_name.encode('utf-8')        
        cursor.close()
        conn.close()
    except:
        print ("Error: unable to fecth data")
        study_case_name = "%s :: Id: (%s)" % (study_case_name, study_case_id)
    
    try:
        email = result[0]
        language = result[1]
        user_full_name = result[2]
        user_full_name = user_full_name.encode('utf-8')
        #logger.debug("User full name: %s" % user_full_name)
    except:
        logger.debug("error reading info user")               

    port = os.getenv('EMAIL_PORT', '587')
    smtp_server = os.getenv('EMAIL_SERVER', 'smtp.gmail.com')
    sender_email = os.getenv('EMAIL_SENDER', 'srst@skaphe.com')    
    password = os.getenv('EMAIL_PASSWORD', 'Skaphe2020*')
    receiver_email = email

    logger.debug("Sending email from %s, smtp: %s, " % (sender_email, smtp_server))       
        
    to = [email]
    subject = 'Waterproof Super Important Message'
    body = 'Hey, what\'s up?\n\n- You'

    email_text = """\
    From: %s
    To: %s 
    Subject: %s

    %s
    """ % (sender_email, ", ".join(to), subject, body)
    status = "Start"
    if (start == False):
        status = "Finish"
    message = MIMEMultipart("alternative")
    message["Subject"] = "Waterproof Execution Models (%s)" % status
    message["From"] = sender_email + " TNC - water-proof.org"
    message["To"] = receiver_email

    current_time = datetime.datetime.now()
   
    html = message_mail('en', start)
    html = html % (user_full_name, study_case_id, study_case_name, current_time)
    html = html.encode('utf-8')    
    part = MIMEText(html, "html")
    message.attach(part)

    try:        
        #server =  smtplib.SMTP_SSL(smtp_server, port)
        server = smtplib.SMTP(smtp_server, port, timeout=20)
        server.starttls()
        server.ehlo()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.close()
        logger.debug ("Email sent!")
    except Exception as e:
        logger.debug ('Something went wrong...: %s' % e)

    return "send mail to: " + user_full_name

def message_mail(language, start):

    if (language == 'en'):
        if (start == True):
            return """\
                <html>
                <body>
                    <p>Dear User %s,</p>
                    <p><br />You started the execution of the process identified with Id: %s for the Case Study: %s.</p>
                    <p>Once the process is finished, we will be sending you an email informing you to review the results.</p>
                    <p>Execution Start Date:% s</p>
                    <p>Regards,</p>
                    <p>Waterproof team</p>
                </body>
                </html>
                """
        else:
            return """\
                <html>
                <body>
                    <p>Dear User %s,</p>
                    
                    <p>Your execution process identified with Id: %s for the Case Study: %s has finished.</p>
                    <p>Finished Date:% s</p>
                    <p>Regards,</p>
                    <p>Waterproof team</p>
                </body>
                </html>
                """

def generate_ms_classes(process_path, activity_portfolios_path):
    """
    Generate mapserver classes for each activity portfolio
    :return:
    """
    #------------------------#
    # GENERATE MAPSERVER CLASSES FOR ACTIVITY PORTFOLIO
    #------------------------#
    print ("GENERATE MAPSERVER CLASSES FOR ACTIVITY PORTFOLIO")
    classes_colors = ["230 39 111","39 230 220","170 230 39","175 96 26","164 39 230","86 39 230","247 220 111","125 102 8","98 101 103","144 148 151","202 207 210","40 55 71","93 109 126","169 204 227"]
    
    ms_lry_tpl = """
        MAP
            NAME          'Waterproof Areas Rios'
            CONFIG        'MS_ERRORFILE' 'stderr'
            EXTENT        -8412553 503524 -8391124 524032
            UNITS         meters
            STATUS        ON
            SIZE          500 500
            RESOLUTION 91
            DEFRESOLUTION 91
            PROJECTION
                'init=epsg:3857'
            END
            INCLUDE '../../../metadata_mapserver.map'
            LAYER
                NAME "NbS_portfolio"
                METADATA
                  'ows_title' 'Areas Rios Suggested'
                END
                INCLUDE '../../../waterproof.projection'
                DATA '04-RIOS/1_investment_portfolio_adviser_workspace/activity_portfolios/activity_portfolio_total.tif'
                TYPE RASTER
                STATUS  OFF    
                CLASSITEM "[pixel]"
                CLASSGROUP 'Areas_Rios'    
                %s
            END
        END
        """
    
    ms_class_tpl = """
            CLASS
                EXPRESSION "%s"
                NAME "%s"
                GROUP "Areas_Rios"
                STYLE
                    COLOR %s
                END
            END
            """
    
    json_file = open(os.path.join(activity_portfolios_path, "activity_raster_id.json"))
    data_activity = json.load(json_file)
    json_file.close()
    ms_classes = ""
    for k, v in data_activity.items():
        ms_classes += ms_class_tpl % (v['index'], k, classes_colors[v['index']])
    
    ms_lry = ms_lry_tpl % ms_classes
    ms_lyr_file = open(os.path.join(process_path, 'areas_rios.map'), 'w')
    ms_lyr_file.write(ms_lry)
    ms_lyr_file.close()

def makeGetRequest(url, parameters, timeout, headers):
    logger.debug("URL :: %s :: Parameters :: %s", url, parameters)
    r = requests.get(url=url, params=parameters)
    data = r.json()
    return data

def preproc_rios(id_usuario, id_case):

  logging.info("*** preproc_rios :: START ***")
  reload(sys)  # Reload is a hack
  sys.setdefaultencoding('UTF8')
    
  sendEmail(id_usuario, id_case, True)

  studyCases_objectives = getStudyCaseObjectives(id_case)
  result = {'message': 'Preprocessing', 'status': 'success'}
  
  objectives={
      'do_erosion':True,
      'do_nutrient_p': True,
      'do_nutrient_n':True,
      'do_flood': True,
      'do_gw_bf': True
  }
  
  do_erosion =  objectives['do_erosion']
  do_np = objectives['do_nutrient_p']
  do_nn = objectives['do_nutrient_n']
  do_flood = objectives['do_flood']
  do_gw_bf = objectives['do_gw_bf']
  
  logging.debug('debug message')
  inputs = {"do_erosion": bool(do_erosion), "do_nutrient_p": bool(do_np), "do_nutrient_n": bool(
      do_nn), "do_flood": bool(do_flood), "do_gw_bf": bool(do_gw_bf)}
  catchments = getStudyCaseCatchments(id_case)
  ptapCatchments=getPtapCatchmentsByStudyCase(id_case)
  catchments=list(set(catchments+ptapCatchments))
  nbsList = getStudyCaseNbs(id_case)
  ptaps=getStudyCasePtaps(id_case)
  catchmentList = []
  ptapList=[]
  base_url_api = 'http://wfapp_py3:8000/wf-models/'
  #base_url_api = 'http://dev.skaphe.com:8000/'
  headers = {
      'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
  }
  #------------------------#
  # EJECUCION EXCHANGE RATE
  #------------------------#
  urlExchageRate = base_url_api + 'exchangeRate'
  parameters = {
      'study_case_id': id_case
  }
  data = makeGetRequest(urlExchageRate, parameters, 5, headers)
  for catch in catchments:
      catchmentList.append(catch[0])
  for ptap in ptaps:
      ptapList.append(ptap[0])
  for counter, catchment in enumerate(catchmentList):
      catchment=str(catchment)
      basinQuery = getCatchmentBasin(catchment)
      basin = str(basinQuery[0])
      catchmentDir='WI_'+catchment
      today = datetime.date.today()
      out_directory = "%s_%s_%s-%s-%s/%s" % (int(id_usuario), int(id_case), today.year, today.month, today.day,catchmentDir)
      print(":::BASIN::: %s" % basin)
      
      obj, outputPath, catchmentOut,pcp_label = executeFunction(basin, catchment, id_usuario, inputs,id_case,catchmentDir)
      list_parameters = execRIOS.getParameters(basin, 'rios')
      print("::CATCHMENT OUT:::")
      print(catchmentOut)
      listObjs = []
      #Asignar lista de objetivos del CE
      for objective in studyCases_objectives:
          listObjs.append(objective[0])

      process_path = "/home/skaphe/Documentos/tnc/modelos/salidas/%s/" % (out_directory)
      # process_path = "/data/outputs/%s/" % (out_directory)
      isdir = os.path.isdir(process_path)
      if(not isdir):
          os.mkdir(process_path)

      isdir = os.path.isdir(process_path + 'out')
      if(not isdir):
          os.mkdir(process_path + 'out')

      isdir = os.path.isdir(process_path + 'in')
      if(not isdir):
          os.mkdir(process_path + 'in')
      
      parameters, out_path = execRIOS.processParameters(nbsList,list_parameters, catchment,id_case,basin, 
                                                    process_path, id_usuario, listObjs, obj, outputPath, 
                                                    catchmentOut,pcp_label)

      execRIOS.execModel(parameters)
      with (open(process_path + 'exec_rios_parameters.json', 'w')) as fp:
          json.dump(parameters, fp)
      # Save report ipa in BD
      parse_to_get_ipa_report(out_path,catchment,id_case,id_usuario)
      
      #*************************#
      exportToShp(catchment, catchmentOut, True)  
      
      #*************************#

      headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
      }
      #------------------------#
      # TRADUCTOR DE COBERTURAS
      #------------------------#
      print ("TRADUCTOR DE COBERTURAS")
      url = base_url_api + 'cobTrans'
      first_nbs=nbsList[0] 
      region = getRegionFromId(basin)
      region_name = region[4]
      path_lulc = process_path + 'in/04-RIOS/LULC_%s.tif' % region_name
      print("path_lulc = %s" % path_lulc) 
      activity_portfolios_path = process_path + 'out/04-RIOS/1_investment_portfolio_adviser_workspace/activity_portfolios'
      parameters = {
          'pathCobs': activity_portfolios_path,
          'nbs_id': first_nbs,
          'basin' : basin,
          'study_case_id' : id_case,
          'pathLULC': path_lulc,
          'catchmentOut': catchmentOut
      }
      data = makeGetRequest(url, parameters, 5, headers)        

      #-----------------------#
      #  EJECUCION DE INVEST  #
      #-----------------------#
      logger.debug("*** Execute Invest ***")
      url = base_url_api + 'execInvest'
      ''' 1. TYPE: CURRENT'''
      parameters = {
              'type': 'current',
              'id_usuario': id_usuario,
              'basin': basin,
              'models': ['sdr', 'awy', 'ndr','carbon','swy'],
              'catchment': catchment,
              'case': id_case
      }
      logger.debug("1. Execute Invest (Current)")
      try:
          data_exec_invest_current = makeGetRequest(url, parameters, 5, headers)
          print(data_exec_invest_current)
      except requests.exceptions.HTTPError as e:
          print (e.response.text)
          logger.warning("error executing::  %s", url)

      #''' 2. type == currentCarbon '''
      # parameters['type'] = 'currentCarbon'

      # try:
      # 	data_exec_invest_current_carbon = exec_preproc.makeGetRequest(url,parameters,5,headers)
      # except:
      # 	logger.warning("error executing::  %s", url)

      ''' 2. TYPE: BaU '''
      # campo analysis_period_value de study_cases
      parameters['type'] = 'BaU'
      logger.debug("2. Execute Invest (BaU) ")
      try:
          data_exec_invest_current = makeGetRequest(url, parameters, 5, headers)
      except:
          logger.warning("error executing::  %s", url)

      # ''' Ejecutar Carbon para BaU'''

      ''' 3. TYPE: NBS '''
      # campo analysis_period_value de study_cases
      parameters['type'] = 'NBS'
      try:
        data_exec_invest_current = makeGetRequest(url,parameters,5,headers)
      except:
        logger.warning("error executing::  %s", url)

      # ''' Ejecutar Carbon para NBS'''

      # # TODO :: Evaluar si se puede optimizar execInvest adicionando los llamados a 'Carbon' directamente en current, BaU y NBS

      #-------------------------#
      # EJECUCION DESAGREGACION
      #-------------------------#
      url = base_url_api + 'disaggregation'
      parameters = {
              'id_usuario': id_usuario,
              'basin': basin,
              'catchment': catchment,
              'case': id_case
      }
      try:
        data_exec_invest_current = makeGetRequest(url,parameters,5,headers)
      except:
        logger.warning("error executing::  %s", url)     
      #-------------------------#
      # EJECUCION WATER BALANCE
      #-------------------------#
      url = base_url_api + 'wbdisaggregationIntake'
      parameters = {
              'user_id': id_usuario,
              'id_intake': catchment,
              'study_case_id': id_case
      }
      try:
        data_exec_invest_current = makeGetRequest(url,parameters,5,headers)
      except:
        logger.warning("error executing::  %s", url)     
      #------------------#
      # EJECUCION ACUEDUCT
      #------------------#
      url = base_url_api + 'aqueduct'
      parameters = {
              'path': process_path,
              'id_intake': catchment
      }
      try:
        data_exec_invest_current = makeGetRequest(url,parameters,5,headers)
      except:
        logger.warning("error executing::  %s", url)    
  #---------------#
  # MODELOS PTAP
  #--------------#
  for counter, ptap in enumerate(ptapList):
      ''' 1. WB DISAGGREGATION'''
      url = base_url_api + 'wbdisaggregationPTAP'
      parameters = {
              'ptap_id': ptap,
              'user_id': id_usuario,
              'study_case_id': id_case
      }
      try:
        data_exec_invest_current = makeGetRequest(url,parameters,5,headers)
      except:
        logger.warning("error executing::  %s", url)   
  #-----------------------------#
  # EJECUCION FUNCIONES DE COSTO
  #-----------------------------#
  url = base_url_api + 'costFunctionExecute'
  parameters = {
          'user_id': id_usuario,
          'intake_id': catchmentList[0],
          'study_case_id': id_case
  }
  try:
      data_exec_invest_current = makeGetRequest(url,parameters,5,headers)
  except:
      logger.warning("error executing::  %s", url)  
  
  #---------------------#
  # EJECUCION INDICATORS
  #---------------------#
  url = base_url_api + 'indicators'
  parameters = {
      'user_id': id_usuario,
      'study_case_id': id_case
  }
  try:
      data_exec_invest_current = makeGetRequest(url,parameters,5,headers)
  except:
      logger.warning("error executing::  %s", url)    

  #---------------#
  # EJECUCION ROI
  #---------------#
  url = base_url_api + 'roiExecution'
  parameters = {
      'user_id': id_usuario,
      'study_cases_id': id_case
  }
  try:
    data_exec_invest_current = makeGetRequest(url,parameters,5,headers)
  except:
    logger.warning("error executing::  %s", url)    

  updateStudyCaseRunAnalisys(id_case)
  try:
    generate_ms_classes(process_path + 'out', activity_portfolios_path)
  except:
    logger.warning("error generate_ms_classes::  %s", activity_portfolios_path)

  try:
      generate_ms_main_file(process_path )
  except:
      logger.warning("error generate_ms_main_file::  %s", process_path)

  try:
      sendEmail(id_usuario, id_case, False)
  except:
      logger.warning("error sendEmail::  %s", id_case)

  return result


def correct_stream(path_prerios):
    print('correct_stream, path: %s' % path_prerios)
    NameDEM     = glob.glob(os.path.join(path_prerios,'DEM*'))
    NameStream  = glob.glob(os.path.join(path_prerios,'Stream*'))

    # Read Raster - Base
    Tmp     = rasterio.open(NameDEM[0])
    Tmp1    = rasterio.open(NameStream[0])
    DEM     = Tmp.read(1)
    NoDataDEM = Tmp.nodata

    Stream  = Tmp1.read(1)
    NoDataStream = Tmp1.nodata

    # Check
    if np.sum(Stream[Stream != NoDataStream]) == 0:
        Posi = DEM == np.min(DEM[DEM != NoDataDEM])
        Stream[Posi] = 1

        Tmp.close()
        Tmp1.close()

        height = Tmp1.shape[0]
        width  = Tmp1.shape[1]
        dtype  = Stream.dtype
        crs    = Tmp1.crs
        transform = Tmp1.transform

        # Lectura
        with rasterio.open(
            NameStream[0],'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=dtype,
            crs=crs,
            transform=transform,
            nodata=NoDataStream
        ) as dst:
            dst.write(Stream, 1)

def generate_ms_main_file(process_path):
    AWY_DIR = "output/per_pixel"
    type_stats=['min','max']
    catchment_relative_path = "in/catchment/catchment.shp"

    shp_file = os.path.join(process_path, catchment_relative_path)
    invest_dir = os.path.join(process_path, "out/03-INVEST")
    if (os.path.exists(invest_dir)):
        awy_dir = os.path.join(invest_dir, "AWY")
        swy_dir = os.path.join(invest_dir, "SWY")
        sdr_dir = os.path.join(invest_dir, "SDR")
        ndr_dir = os.path.join(invest_dir, "NDR")
        carbon_dir = os.path.join(invest_dir, "CARBON")
        min_swy = -1
        max_swy = 1
        min_awy = -1
        max_awy = 1
        min_sdr = -1
        max_sdr = 1
        min_ndrn = -1
        max_ndrn = 1
        min_ndrp = -1
        max_ndrp = 1
        min_carbon = -1
        max_carbon = 1

        if (os.path.exists(awy_dir)):
            print("AWY directory found: %s" % awy_dir)
            for year_dir in os.listdir(awy_dir):
                print("Year directory found: %s" % year_dir)
                if os.path.isdir(os.path.join(awy_dir, year_dir)):
                    full_path_awy = os.path.join(awy_dir, year_dir, AWY_DIR)
                    if (os.path.exists(full_path_awy)):
                        for awy_file in os.listdir(full_path_awy):
                            if awy_file.startswith("wyield_"):
                                awy_raster_file = os.path.join(full_path_awy, awy_file)
                                stats = zonal_stats(shp_file,awy_raster_file,stats=type_stats)
                                print(stats)
                                min_awy = stats[0]['min']
                                max_awy = stats[0]['max']
        if (os.path.exists(swy_dir)):
            print("SWY directory found: %s" % swy_dir)
            for year_dir in os.listdir(swy_dir):
                print("Year directory found: %s" % year_dir)
                if os.path.isdir(os.path.join(swy_dir, year_dir)):
                    full_path_swy = os.path.join(swy_dir, year_dir)
                    if (os.path.exists(full_path_swy)):
                        for swy_file in os.listdir(full_path_swy):
                            if swy_file.startswith("B_") and swy_file.endswith(".tif"):
                                swy_raster_file = os.path.join(full_path_swy, swy_file)
                                stats = zonal_stats(shp_file,swy_raster_file,stats=type_stats)
                                print(stats)
                                min_swy = stats[0]['min']
                                max_swy = stats[0]['max']
        if (os.path.exists(sdr_dir)):
            print("SDR directory found: %s" % sdr_dir)
            for year_dir in os.listdir(sdr_dir):
                print("Year directory found: %s" % year_dir)
                if os.path.isdir(os.path.join(sdr_dir, year_dir)):
                    full_path_sdr = os.path.join(sdr_dir, year_dir)
                    if (os.path.exists(full_path_sdr)):
                        for sdr_file in os.listdir(full_path_sdr):
                            if sdr_file.startswith("B_"):
                                sdr_raster_file = os.path.join(full_path_sdr, sdr_file)
                                stats = zonal_stats(shp_file,sdr_raster_file,stats=type_stats)
                                print(stats)
                                min_sdr = stats[0]['min']
                                max_sdr = stats[0]['max']
        if (os.path.exists(ndr_dir)):
            print("NDR directory found: %s" % ndr_dir)
            for year_dir in os.listdir(ndr_dir):
                print("Year directory found: %s" % year_dir)
                if os.path.isdir(os.path.join(ndr_dir, year_dir)):
                    full_path_ndr = os.path.join(ndr_dir, year_dir)
                    if (os.path.exists(full_path_ndr)):
                        for ndr_file in os.listdir(full_path_ndr):
                            if ndr_file.startswith("n_export_"):
                                ndr_raster_file = os.path.join(full_path_ndr, ndr_file)
                                stats = zonal_stats(shp_file,ndr_raster_file,stats=type_stats)
                                print ("NDR N")
                                print(stats)
                                min_ndrn = stats[0]['min']
                                max_ndrn = stats[0]['max']
                            elif ndr_file.startswith("p_export_"):
                                ndr_raster_file = os.path.join(full_path_ndr, ndr_file)
                                stats = zonal_stats(shp_file,ndr_raster_file,stats=type_stats)
                                print ("NDR P")
                                print(stats)
                                min_ndrp = stats[0]['min']
                                max_ndrp = stats[0]['max']
        if (os.path.exists(carbon_dir)):
            print("CARBON directory found: %s" % carbon_dir)
            for year_dir in os.listdir(carbon_dir):
                print("Year directory found: %s" % year_dir)
                if os.path.isdir(os.path.join(carbon_dir, year_dir)):
                    full_path_carbon = os.path.join(carbon_dir, year_dir)
                    if (os.path.exists(full_path_carbon)):
                        for carbon_file in os.listdir(full_path_carbon):
                            if carbon_file.startswith("tot_c_cur_"):
                                carbon_raster_file = os.path.join(full_path_carbon, carbon_file)
                                stats = zonal_stats(shp_file,carbon_raster_file,stats=type_stats)
                                print(stats)
                                min_carbon = stats[0]['min']
                                max_carbon = stats[0]['max']

        mapfile = ms_templates.mapserver_template_file.format(min_awy,max_awy,min_swy,max_swy,min_sdr,max_sdr,min_ndrn,max_ndrn,min_ndrp,max_ndrp,min_carbon,max_carbon)

        f = open(os.path.join(process_path, "mapserver.map"),"w+")
        f.write(mapfile)
        f.close()