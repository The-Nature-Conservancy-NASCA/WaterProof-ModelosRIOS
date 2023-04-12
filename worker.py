import os, sys
import time
import logging
import exec_preproc
from celery import Celery

logger = logging.getLogger(__name__) # grabs underlying WSGI logger
logger.setLevel(logging.DEBUG)

celery = Celery('worker_rios')
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379")


@celery.task(name="create_task", queue="worker_rios")
def create_task(task_type):
    time.sleep(int(task_type) * 10)
    return True

@celery.task(name="send_mail_task", queue="worker_rios")
def send_mail_task(id_usuario, id_case, start):
    logger.debug("send_mail_task :: start")
    reload(sys)  # Reload is a hack    
    sys.setdefaultencoding('UTF8')
    user = exec_preproc.sendEmail(id_usuario, id_case, start)
    return user  

@celery.task(name="preproc_rios_task", queue="worker_rios")
def preproc_rios_task(id_usuario, id_case):
    logger.debug("preproc_rios_task :: start")
    result = exec_preproc.preproc_rios(id_usuario, id_case)
    return result
  
