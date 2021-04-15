from flask import Flask
from exec_preproc import executeFunction,getStudyCaseCatchments,getCatchmentBasin
from execRIOS import getParameters,processParameters,execModel
from flask import request
from flask import jsonify
import datetime
import logging
import requests
import debugpy
import ptvsd
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
	#basin = request.args.get('basin')
	#catchment = str(request.args.get('catchment'))
	id_usuario = request.args.get('id_usuario')
	id_case=request.args.get('id_case')
	logging.debug('debug message')
	# print(user)
	inputs = {"do_erosion":bool(do_erosion),"do_nutrient_p":bool(do_np),"do_nutrient_n":bool(do_nn),"do_flood":bool(do_flood),"do_gw_bf":bool(do_gw_bf)}
	catchments=getStudyCaseCatchments(id_case)
	catchmentList=[]
	for catch in catchments:
		catchmentList.append(catch[0])
	catchment=str(catchmentList[0])
	basinQuery=getCatchmentBasin(catchment)
	basin=str(basinQuery[0])
	print(":::BASIN:::")
	print(basin)
	obj, outputPath, catchmentOut = executeFunction(basin,catchment,id_usuario,inputs)
	listP = getParameters(basin,'rios')
	print ("::CATCHMENT OUT:::")
	print(catchmentOut)
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

	parameters,out_path = processParameters(listP,basin,"/home/skaphe/Documentos/tnc/modelos/salidas/9_2020_10_24/",id_usuario,listObjs,obj, outputPath, catchmentOut)

	# print(parameters)
	
	execModel(parameters)

	headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
	}

	url = 'http://dev.skaphe.com:8000/cobTrans'

	parameters = {
		'pathCobs' : '/home/skaphe/Documentos/tnc/modelos/salidas/9_2020_10_24/out/04-RIOS/1_investment_portfolio_adviser_workspace/activity_portfolios/continuous_activity_portfolios',
		'nbs_id': 5,
		'pathLULC': '/home/skaphe/Documentos/tnc/modelos/salidas/9_2020_10_24/in/04-RIOS/LULC_SA_1.tif'
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

	# TODO :: Ejecutar desagregacion

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
	# debugpy.listen(5678)
	ptvsd.enable_attach(address=('0.0.0.0', 5678), redirect_output=True)
	app.run(host='0.0.0.0', port=5050)

