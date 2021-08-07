from flask import Flask
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


@app.route('/welcome/', methods=['GET'])
def welcome():
    result = {'message': 'Welcome to RIOS API', 'status': 'success'}
    return result


@app.route("/preprocRIOS", methods=['GET'])
def execPreproc():
    id_usuario = request.args.get('id_usuario')
    id_case = request.args.get('id_case')
    studyCases_objectives = exec_preproc.getStudyCaseObjectives(id_case)
    result = {'message': 'Preprocessing', 'status': 'success'}
    objectives={
        'do_erosion':True,
        'do_nutrient_p': True,
        'do_nutrient_n':True,
        'do_flood': True,
        'do_gw_bf': True
    }
    
    # for obj in studyCases_objectives:
    #     # Erosion control for drinking wwater quality RIOS
    #     if (obj[0]==1):
    #         objectives['do_erosion']=True
    #     # Erosion control for reservoir maintenance RIOS
    #     elif (obj[0]==2):
    #         objectives['do_erosion']=True
    #     # Nutrient retention (Phosporous) RIOS
    #     elif (obj[0]==3):
    #         objectives['do_nutrient_p']=True
    #     # Nutrient retention (Nitrogen) RIOS
    #     elif (obj[0]==4):
    #         objectives['do_nutrient_n']=True 
    #     # Flood mitigation RIOS
    #     elif (obj[0]==5):
    #         objectives['do_flood']=True
    #     # Groundwater recharge enhancement RIOS        
    #     elif (obj[0]==6):
    #         objectives['do_gw_bf']=True
    #     # Baseflow RIOS
    #     else:
    #         objectives['do_gw_bf']=True
    #     print(obj)

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
    base_url_api = 'http://wfapp_py3:8000/'
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

        # if do_erosion:
        #     listObjs.append(2)
        #     listObjs.append(3)

        # if do_np:
        #     listObjs.append(5)

        # if do_nn:
        #     listObjs.append(4)

        # if do_flood:
        #     listObjs.append(6)

        # if do_gw_bf:
        #     listObjs.append(7)
        #     listObjs.append(8)

        process_path = "/home/skaphe/Documentos/tnc/modelos/salidas/%s/" % (
            out_directory)
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
        parameters = {
            'pathCobs': process_path + 'out/04-RIOS/1_investment_portfolio_adviser_workspace/activity_portfolios/continuous_activity_portfolios',
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

    return result

def str2bool(v):
    return v.lower() in ("true", "True")

def makeGetRequest(url, parameters, timeout, headers):
    logger.debug("URL :: %s :: Parameters :: %s", url, parameters)
    r = requests.get(url=url, params=parameters)
    data = r.json()
    return data

if __name__ == '__main__':
    logger.debug("start debugging port :: 5678")
    #debugpy.listen(5678)
    ptvsd.enable_attach(address=('0.0.0.0', 5678), redirect_output=True)
    app.run(host='0.0.0.0', port=5050)
