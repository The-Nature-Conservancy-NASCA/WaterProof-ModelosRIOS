from flask import Flask, jsonify
import exec_preproc
from execRIOS import getParameters,processParameters,execModel
from flask import request
import datetime
import logging
import requests
import os
import debugpy
import ptvsd
import json
import sys
from celery.result import AsyncResult
import worker

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
    logging.info("*** preprocRIOS :: START ***")
    id_usuario = request.args.get('id_usuario')
    id_case = request.args.get('id_case')
    result = exec_preproc.preproc_rios(id_usuario, id_case)
    return jsonify(result)

def str2bool(v):
    return v.lower() in ("true", "True")

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

@app.route("/wf-rios/tasks/", methods=['GET', 'POST'])
def get_status():
    if request.method == 'GET':
        task_id = request.args.get('id')
        task_result = AsyncResult(task_id)        
        result = validate_task_result(task_result)
        return jsonify(result)
    else:
        request_data = request.get_json()
        print (request_data)
        task_type = request_data["type"]
        task = worker.create_task.delay(int(task_type))
        task_result = AsyncResult(task.id)
        return jsonify({"task_id": task.id})        

@app.route("/wf-rios/task_mail/", methods=['GET', 'POST'])
def task_mail():
    if request.method == 'GET':
        id_usuario = request.args.get('id_usuario')
        id_case = request.args.get('id_case')
        task = worker.send_mail_task.delay(id_usuario, id_case, True)
        task_result = AsyncResult(task.id)        
        result = validate_task_result(task_result)
        return jsonify(result)

@app.route("/wf-rios/preproc_rios_task/", methods=['GET'])
def preproc_rios_task():
    logger.debug("*** preproc_rios_task :: START ***")
    id_usuario = request.args.get('id_usuario')
    id_case = request.args.get('id_case')
    task = worker.preproc_rios_task.delay(id_usuario, id_case)
    task_result = AsyncResult(task.id)        
    result = validate_task_result(task_result)
    return jsonify(result)

def validate_task_result(task_result):
    result = task_result.result
    status = task_result.status
    if status == 'FAILURE':
        result = 'Error'
    resp = {
        "task_id": task_result.id,
        "task_status": status,
        "task_result": result
    }
    return resp

if __name__ == '__main__':
    logger.debug("start debugging port :: 5678")
    #debugpy.listen(5678)
    #ptvsd.enable_attach(address=('0.0.0.0', 5678), redirect_output=True)
    reload(sys)  # Reload is a hack
    sys.setdefaultencoding('UTF8')
    app.run(host='0.0.0.0', port=5050, debug=True)

