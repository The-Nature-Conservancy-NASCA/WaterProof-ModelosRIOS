from flask import Flask
from exec_preproc import executeFunction
from execRIOS import getParameters,processParameters,execModel
from flask import request
from flask import jsonify
import logging

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
	catchment = request.args.get('catchment')
	id_usuario = request.args.get('id_usuario')
	# print(user)
	
	
	inputs = {"do_erosion":bool(do_erosion),"do_nutrient_p":bool(do_np),"do_nutrient_n":bool(do_nn),"do_flood":bool(do_flood),"do_gw_bf":bool(do_gw_bf)}
	# print(inputs)
	obj, outputPath = executeFunction(basin,catchment,id_usuario,inputs)

	listP = getParameters(basin,'rios')

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

	parameters,out_path = processParameters(listP,basin,"/home/skaphe/Documentos/tnc/modelos/salidas/9_2020_10_24/",id_usuario,listObjs,obj, outputPath)

	print(parameters)
	
	execModel(parameters)

	return "Exito"
	# user = request.args.get('nm')

def str2bool(v):
  return v.lower() in ("true", "True")

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5050)