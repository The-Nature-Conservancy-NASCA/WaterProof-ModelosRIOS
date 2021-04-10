from flask import Flask
from exec_preproc import executeFunction,getStudyCaseCatchments,getCatchmentBasin
from execRIOS import getParameters,processParameters,execModel
from flask import request
from flask import jsonify
import logging
import requests

app = Flask(__name__)

logger = logging.getLogger('werkzeug') # grabs underlying WSGI logger
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
	catchment = str(request.args.get('catchment'))
	id_usuario = request.args.get('id_usuario')
	id_case=request.args.get('id_case')
	logging.debug('debug message')
	# print(user)
	inputs = {"do_erosion":bool(do_erosion),"do_nutrient_p":bool(do_np),"do_nutrient_n":bool(do_nn),"do_flood":bool(do_flood),"do_gw_bf":bool(do_gw_bf)}
	catchments=getStudyCaseCatchments(id_case)
	catchmentList=[]
	print("CATCHMENT TYPE:::")
	print(type(catchment))
	for catch in catchments:
		print("::SPLIT::::")
		print(catch[0])
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

	data = makeGetRequest(url,parameters,5,headers)

	print(data)


	return "Exito"
	# user = request.args.get('nm')

def str2bool(v):
  return v.lower() in ("true", "True")

def makeGetRequest(url,parameters,timeout,headers):
	r = requests.get(url=url,params=parameters)
	data = r.json()
	return data


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5050)

