from flask import Flask
from exec_preproc import executeFunction
from execRIOS import getParameters,processParameters,execModel
from flask import request
from flask import jsonify
import date
import logging
import requests
import debugpy
app = Flask(__name__)
logger = logging.getLogger('rios_api') # grabs underlying WSGI logger
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('test.log') # creates handler for the log file
logger.addHandler(handler) # adds handler to the werkzeug WSGI logger

@app.route('/welcome/', methods=['GET'])
def welcome():
	return "Welcome to localhost:5050"

@app.route("/preprocRIOS", methods=['GET'])
def execPreproc():
	#do_erosion,do_np, do_nn, do_flood,do_gw_bf,basin,catchment,id_usuario
	# print(request.args.get('do_np'))
	do_erosion = str2bool(request.args.get('do_erosion'))
	do_np = str2bool(request.args.get('do_np'))
	do_nn = str2bool(request.args.get('do_nn'))
	do_flood = str2bool(request.args.get('do_flood'))
	do_gw_bf = str2bool(request.args.get('do_gw_bf'))
	basin = request.args.get('basin')
	catchment = request.args.get('catchment')
	id_usuario = request.args.get('id_usuario')
	study_case_id = request.args.get('study_case_id'),
	nbs_id = request.args.get('nbs_id'),
	# print(user)
	logger.debug("start execPreProc")
	
	inputs = {"do_erosion":bool(do_erosion),"do_nutrient_p":bool(do_np),"do_nutrient_n":bool(do_nn),"do_flood":bool(do_flood),"do_gw_bf":bool(do_gw_bf)}
	# print(inputs)
	date = datetime.date.today()
	out_directory = "%s-%s-%s-%s-%s-%s" % {id_usuario, study_case_id, catchment, date.year, date.month, date.day}
	obj, outputPath, catchmentOut = executeFunction(basin,catchment,id_usuario,inputs, study_case_id, out_directory)

	list_parameters = getParameters(basin,'rios')

	listObjs = []
	
	if do_erosion:
		listObjs.append(2)
		listObjs.append(3)
	
	if do_np:
		listObjs.append(5)

	if do_nn:
		listObjs.append(4)

	if do_flood:
		listObjs.append(6)

	if do_gw_bf:
		listObjs.append(7)
		listObjs.append(8)
	
	process_path = "/home/skaphe/Documentos/tnc/modelos/salidas/%s/" % {out_directory}
	parameters,out_path = processParameters(list_parameters,basin,process_path,id_usuario,listObjs,obj, outputPath, catchmentOut)

	# print(parameters)
	
	execModel(parameters)

	headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
	}
	base_url_api = "http://wfapp_py3_container:8000/"
	base_url_api = "http://dev.skaphe.com:8000/"
	url = base_url_api + 'cobTrans'
	# Se debe iterar de acuerdo al numero de captaciones q pueda llegar a tener el caso de estudio
	parameters = {
		'pathCobs' : process_path + 'out/04-RIOS/1_investment_portfolio_adviser_workspace/activity_portfolios/continuous_activity_portfolios',
		'nbs_id': nbs_id,
		'pathLULC': process_path + 'in/04-RIOS/LULC_SA_1.tif'
	}

	data = makeGetRequest(url,parameters,nbs_id,headers)

	''' Code for execInvest'''
	''' 1. type == current '''
	url = base_url_api + 'execInvest'

	parameters = {
		'type' : 'current',
		'id_usuario': id_usuario, #1,
		'basin' : basin,  # 44,
		'models' : ['sdr','awy','ndr'],
		'catchment' : catchment, #1,
	}

	''' 1. type == current '''
	try:
		data_exec_invest_current = makeGetRequest(url,parameters,nbs_id,headers)
	except:
		logging.warning("error executing::  %s", url)

	''' 2. type == currentCarbon '''
	
	parameters = {
		'type' : 'currentCarbon',
		'id_usuario': id_usuario, #1,
		'basin' : basin,  # 44,
		'models' : ['sdr','awy','ndr'],
		'catchment' : catchment, #1,
	}
	try:
		data_exec_invest_current_carbon = makeGetRequest(url,parameters,nbs_id,headers)
	except:
		logging.warning("error executing::  %s", url)


	''' 3. type == BaU '''
	# campo analysis_period_value de study_cases
	try:
		data_exec_invest_current = makeGetRequest(url,parameters,nbs_id,headers)
	except:
		logging.warning("error executing::  %s", url)

	''' Ejecutar Carbon para BaU'''

	''' 4. type == NBS '''
	# campo analysis_period_value de study_cases
	try:
		data_exec_invest_current = makeGetRequest(url,parameters,nbs_id,headers)
	except:
		logging.warning("error executing::  %s", url)

	''' Ejecutar Carbon para NBS'''

	# TODO :: Evaluar si se puede optimizar execInvest adicionando los llamador a 'Carbon' directamente en current, BaU y NBS

	# TODO :: Ejecutar ¡¡¡ desagregacion !!!

	# TODO :: Ejecutar WB 

	# TODO :: Ejecutar Cost Functions

	# TODO :: Ejecutar ROI

	# 

	print(data)


	return "Exito"
	# user = request.args.get('nm')

def str2bool(v):
  return v.lower() in ("true", "True")

def makeGetRequest(url,parameters,timeout,headers):
	logger.debug("URL :: %s :: Parameters :: %s", url, parameters)
	r = requests.get(url=url,params=parameters)
	data = r.json()
	return data


if __name__ == '__main__':
	logging.debug("start debugging port :: 5678")
	debugpy.listen(5678)
	app.run(host='0.0.0.0', port=5050)

