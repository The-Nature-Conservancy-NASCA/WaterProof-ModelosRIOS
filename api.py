from flask import Flask
from exec_preproc import executeFunction
from flask import request
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
	do_erosion = bool(request.args.get('do_erosion'))
	do_np = bool(request.args.get('do_np'))
	do_nn = bool(request.args.get('do_nn'))
	do_flood = bool(request.args.get('do_flood'))
	do_gw_bf = bool(request.args.get('do_gw_bf'))
	basin = request.args.get('basin')
	catchment = request.args.get('catchment')
	id_usuario = request.args.get('id_usuario')
	# print(user)
	
	inputs = {"do_erosion":do_erosion,"do_nutrient_p":do_np,"do_nutrient_n":do_nn,"do_flood":do_flood,"do_gw_bf":do_gw_bf}
	executeFunction(basin,catchment,id_usuario,inputs)
	return "Exito"
	# user = request.args.get('nm')

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5050)