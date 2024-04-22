from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging
from datetime import datetime 
from qiskit_ibm_runtime import QiskitRuntimeService, Session
# import sys
# logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def est_exec_curr_time(job):
    job_metrics=job.metrics()
    created_time=datetime.strptime(job_metrics['timestamps']['created'], '%Y-%m-%dT%H:%M:%S.%fZ')
    est_com_time=datetime.strptime(job_metrics['estimated_completion_time'], '%Y-%m-%dT%H:%M:%S.%fZ') 
    print(job.metrics())
    diff=est_com_time-created_time
    # print(diff)
    # check_time=datetime.utcnow()+diff
    return diff

def user_function(xfaas_object) -> SerWOObject:
  try:
    logging.info("We are in the fn")
    body=xfaas_object.get_body()
    if "Deadline" in body:
      body["Deadline"]=datetime.strptime(body["Deadline"], "%Y-%m-%d %H:%M:%S.%f")
    logging.info(str(body["Deadline"]))
    # logging.info(type(body["Deadline"]))
    # logging.info("Body:"+json.dumps(body))
    # logging.info("Job Id"+json.dumps(body["sub-experiments"]["0"]["id"]))
    # Awaited_job_ids = body["Awaited_job_ids"]
    # logging.info("Job Id:"+str(job_ids))
    logging.info("We are in the fn line 1")
    service = QiskitRuntimeService(channel='ibm_quantum',instance='ibm-q/open/main',token='0657963f91c2cee472772a9e0829a5d37b3f303025acd176a077aa4de8fddfeb496e409e0221a1fc8b5ed75eef435efd974ba2811e5c69380422e5adab61c6eb')
    session = Session(service=service, backend=body['backend'])
    dict=body['submit_job_ids']
    li=[]
    for key in dict:
      job_id=dict[key]
      job= service.job(job_id)
      wait_time=est_exec_curr_time(job)
      li.append(wait_time)
    mt=max(li)
    logging.info("List:"+str(li))
    logging.info("Maximum Waiting time:"+str(mt))
    body["Poll"]=True if datetime.now()<mt else False
    body["Deadline"]=mt
    return SerWOObject(body=body)
  except Exception as e:
    logging.info(e)
    logging.info(e)
    logging.info("Error in Poll function")
    raise Exception("[SerWOLite-Error]::Error at user function",e)

# f=open("/home/tarun/XFaaS/serwo/examples/NewQuantumWorkflow/submit_out.json")
# body=json.load(f)
# body=json.loads(body)
# z=user_function(SerWOObject(body=body))
# body=z.get_body()
# obj=json.dumps(body,default=str)
# with open("/home/tarun/XFaaS/serwo/examples/NewQuantumWorkflow/submit_out.json", "w") as f:
#   json.dump(obj, f)
# logging.info("Output object:"+str(body))