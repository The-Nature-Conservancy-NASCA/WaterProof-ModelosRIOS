from flask import Flask, jsonify
import exec_preproc
from execRIOS import getParameters,processParameters,execModel
from flask import request
from flask import jsonify
import datetime
import logging
import requests
import os
import debugpy
import ptvsd
import json
app = Flask(__name__)
logger = logging.getLogger(__name__)  # grabs underlying WSGI logger
logger.setLevel(logging.DEBUG)
# handler = logging.FileHandler('test.log') # creates handler for the log file
# logger.addHandler(handler) # adds handler to the werkzeug WSGI logger


@app.route('/wf-rios/welcome/', methods=['GET'])
def welcome():
    result = {'message': 'Welcome to RIOS API', 'status': 'success'}
    return jsonify(result)

@app.route('/wf-rios/test-invest/', methods=['GET'])
def test_invest():
    user_id = request.args.get('user_id')
    study_case_id = request.args.get('study_case_id')
    status = request.args.get('status')
    base_url_api = 'http://wfapp_py3:8000/wf-models/'
    r = requests.get(url=base_url_api)
    data = r.json()    
    
    data['user'] = user_id
    exec_preproc.sendEmail(user_id, study_case_id, status == 'start')
    return jsonify(data)

@app.route('/wf-rios/ms_classes/', methods=['GET'])
def test_generate_ms_classes():
    print("TEST GENERATE MAPSERVER CLASSES FOR ACTIVITY PORTFOLIO")
    usr_folder = request.args.get('usr_folder')
    catchment = request.args.get('catchment')
    wi_folder = 'WI_'+catchment
    out_directory = "%s/%s" % (usr_folder, wi_folder)
    # process_path = "/data/outputs/%s/%s/" % (out_directory,'out')
    process_path = "/home/skaphe/Documentos/tnc/modelos/salidas/%s/%s/" % (out_directory, 'out')
    activity_portfolios_path = process_path + '04-RIOS/1_investment_portfolio_adviser_workspace/activity_portfolios'
    print (activity_portfolios_path)
    generate_ms_classes(process_path, activity_portfolios_path)
    result = {'message': 'Generate map file', 'status': 'success'}
    return jsonify(result)


@app.route("/wf-rios/preprocRIOS", methods=['GET'])
def execPreproc():
    id_usuario = request.args.get('id_usuario')
    id_case = request.args.get('id_case')
    studyCases_objectives = exec_preproc.getStudyCaseObjectives(id_case)
    result = {'message': 'Preprocessing', 'status': 'success'}

    exec_preproc.sendEmail(id_usuario, id_case, True)

    objectives={
        'do_erosion':True,
        'do_nutrient_p': True,
        'do_nutrient_n':True,
        'do_flood': True,
        'do_gw_bf': True
    }
    
      #do_erosion,do_np, do_nn, do_flood,do_gw_bf,basin,catchment,id_usuario
    # print(request.args.get('do_np'))
    do_erosion =  objectives['do_erosion']
    do_np = objectives['do_nutrient_p']
    do_nn = objectives['do_nutrient_n']
    do_flood = objectives['do_flood']
    do_gw_bf = objectives['do_gw_bf']
   
    #basin = request.args.get('basin')
    #catchment = str(request.args.get('catchment'))
    logging.debug('debug message')
    inputs = {"do_erosion": bool(do_erosion), "do_nutrient_p": bool(do_np), "do_nutrient_n": bool(
        do_nn), "do_flood": bool(do_flood), "do_gw_bf": bool(do_gw_bf)}
    catchments = exec_preproc.getStudyCaseCatchments(id_case)
    ptapCatchments=exec_preproc.getPtapCatchmentsByStudyCase(id_case)
    catchments=list(set(catchments+ptapCatchments))
    nbsList = exec_preproc.getStudyCaseNbs(id_case)
    ptaps=exec_preproc.getStudyCasePtaps(id_case)
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
        basinQuery = exec_preproc.getCatchmentBasin(catchment)
        basin = str(basinQuery[0])
        catchmentDir='WI_'+catchment
        today = datetime.date.today()
        out_directory = "%s_%s_%s-%s-%s/%s" % (int(id_usuario), int(id_case), today.year, today.month, today.day,catchmentDir)
        print(":::BASIN:::")
        print(basin)
        obj, outputPath, catchmentOut,pcp_label = exec_preproc.executeFunction(basin, catchment, id_usuario, inputs,id_case,catchmentDir)
        list_parameters = getParameters(basin, 'rios')
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
        
        parameters, out_path = processParameters(
            nbsList,list_parameters, catchment,id_case,basin, process_path, id_usuario, listObjs, obj, outputPath, catchmentOut,pcp_label)

        execModel(parameters)
        with (open(process_path + 'exec_rios_parameters.json', 'w')) as fp:
            json.dump(parameters, fp)
        # Save report ipa in BD
        exec_preproc.parse_to_get_ipa_report(out_path,catchment,id_case,id_usuario)
        headers = {
             'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
        }
        #------------------------#
        # TRADUCTOR DE COBERTURAS
        #------------------------#
        print ("TRADUCTOR DE COBERTURAS")
        url = base_url_api + 'cobTrans'
        first_nbs=nbsList[0] 
        region = exec_preproc.getRegionFromId(basin)
        region_name = region[4]
        path_lulc = process_path + 'in/04-RIOS/LULC_%s.tif' % region_name
        print("path_lulc = %s" % path_lulc) 
        activity_portfolios_path = process_path + 'out/04-RIOS/1_investment_portfolio_adviser_workspace/activity_portfolios'
        parameters = {
            'pathCobs': activity_portfolios_path,
            'nbs_id': first_nbs,
            'basin' : basin,
            'study_case_id' : id_case,
            'pathLULC': path_lulc
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
        # 	data_exec_invest_current_carbon = makeGetRequest(url,parameters,5,headers)
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

        # # TODO :: Evaluar si se puede optimizar execInvest adicionando los llamador a 'Carbon' directamente en current, BaU y NBS

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

    exec_preproc.updateStudyCaseRunAnalisys(id_case)
    try:
        generate_ms_classes(process_path + 'out', activity_portfolios_path)
    except:
        logger.warning("error generate_ms_classes::  %s", activity_portfolios_path)

    try:
        exec_preproc.sendEmail(id_usuario, id_case, False)
    except:
        logger.warning("error sendEmail::  %s", id_case)

    return jsonify(result)


def generate_ms_classes(process_path, activity_portfolios_path):
    """
    Generate mapserver classes for each activity portfolio
    :return:
    """
    #------------------------#
    # GENERATE MAPSERVER CLASSES FOR ACTIVITY PORTFOLIO
    #------------------------#
    print ("GENERATE MAPSERVER CLASSES FOR ACTIVITY PORTFOLIO")
    classes_colors = ["19 141 117","25 111 61","34 153 84","175 96 26","243 156 18","241 196 15","247 220 111","125 102 8","98 101 103","144 148 151","202 207 210","40 55 71","93 109 126","169 204 227"]
    
    ms_lry_tpl = """
        MAP
            NAME          'Waterproof Areas Rios'
            CONFIG        'MS_ERRORFILE' 'stderr'
            EXTENT        -8412553 503524 -8391124 524032
            UNITS         meters
            STATUS        ON
            SIZE          5000 5000
            RESOLUTION 91
            DEFRESOLUTION 91
            PROJECTION
                'init=epsg:3857'
            END
            INCLUDE '../../../metadata_mapserver.map'
            LAYER
                NAME "Areas_Rios"
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

def str2bool(v):
    return v.lower() in ("true", "True")

def makeGetRequest(url, parameters, timeout, headers):
    logger.debug("URL :: %s :: Parameters :: %s", url, parameters)
    r = requests.get(url=url, params=parameters)
    data = r.json()
    return data

@app.route("/wf-rios/updateStudyCase", methods=['GET'])
def updateStudyCase():
    id_case = request.args.get('id_case')
    exec_preproc.updateStudyCaseRunAnalisys(id_case)
    result = {'message': 'updateStudyCase', 'status': 'success'}
    return jsonify(result)

@app.route("/wf-rios/queryStudyCaseAnalisysResult", methods=['GET'])
def queryStudyCaseAnalisysResult():
    id_case = request.args.get('id_case')
    result_db = exec_preproc.queryStudyCaseRunAnalisys(id_case)
    result = {'message': 'queryStudyCaseAnalisysResult', 'status': result_db}
    return jsonify(result)

if __name__ == '__main__':
    logger.debug("start debugging port :: 5678")
    #debugpy.listen(5678)
    ptvsd.enable_attach(address=('0.0.0.0', 5678), redirect_output=True)
    app.run(host='0.0.0.0', port=5050)
