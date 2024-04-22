from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging
from circuit_knitting.cutting import reconstruct_expectation_values
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit.quantum_info import PauliList
# import sys
# logging.basicConfig(stream=sys.stdout, level=logging.INFO)
from enum import Enum
class WeightType(Enum):
    EXACT = 1
    SAMPLED = 2
def serialize_enum(enum_obj):
    return enum_obj.name

# Deserialization function to convert string to enum object
def deserialize_enum(enum_str):
    return WeightType[enum_str]

def desterilize_enum_list(list):
  n_list=[]
  # print("list:",list)
  for obj in list:
    a,b=obj
    b=deserialize_enum(b)
    n_list.append((a,b))
  # print("desterilize_enum_list",n_list)
  return n_list  

def observable_dict_desterilizer(dict):
  for key in dict:
    var= dict[key]
    dict[key]= PauliList(var)
  return dict


def user_function(xfaas_object) -> SerWOObject:
  try:
    logging.info("We are in the fn")
    body=xfaas_object.get_body()
    coefficient = body["coefficients"]
    coefficients=desterilize_enum_list(coefficient)
    subobservables = observable_dict_desterilizer(body["subobservables"])
    logging.info("subobservables:"+str(subobservables))

    service = QiskitRuntimeService(channel='ibm_quantum',instance='ibm-q/open/main',token='0657963f91c2cee472772a9e0829a5d37b3f303025acd176a077aa4de8fddfeb496e409e0221a1fc8b5ed75eef435efd974ba2811e5c69380422e5adab61c6eb')   
    # backend = service.get_backend('ibm_brisbane')
    # jobs=service.jobs(backend_name='ibm_brisbane')
    # print("Jobs:",jobs)
    # job_ids=['cr08c4gdvs8g008j82kg','cr08h4m8gdp0008fxrmg']
    # job1=service.job(job_ids[0])
    # job2=service.job(job_ids[1])
    # results={'A':job1.result(), 'B':job2.result()}
    results={}
    job_ids=body["submit_job_ids"]
    logging.info(str(job_ids))
    for key in job_ids:
       job_id=job_ids[key]
       job=service.job(job_id)
       results[key]=job.result()
    logging.info("Results:"+str(results))

    # service = QiskitRuntimeService(channel='ibm_quantum',instance='ibm-q/open/main',token='0657963f91c2cee472772a9e0829a5d37b3f303025acd176a077aa4de8fddfeb496e409e0221a1fc8b5ed75eef435efd974ba2811e5c69380422e5adab61c6eb')    
    # backend = service.get_backend('ibm_brisbane')
    # session = Session(backend=backend)
    reconstructed_expvals = reconstruct_expectation_values(
                results=results,
                coefficients=coefficients,
                observables=subobservables,
    )
    logging.info("Reconstruction Results:"+str(reconstructed_expvals))
    body['Reconstruction_results']=reconstructed_expvals
    body["message"]="Reconstruction completed sucessfully"
    return SerWOObject(body=body)
  except Exception as e:
    logging.info(e)
    logging.info(e)
    logging.info("Error in Invoke function")
    raise Exception("[SerWOLite-Error]::Error at user function",e)
  
# f=open("/home/tarun/XFaaS/serwo/examples/NewQuantumWorkflow/submit_out.json")
# body=json.load(f)
# body=json.loads(body)
# z=user_function(SerWOObject(body=body))
# body=z.get_body()
# obj=json.dumps(body,default=str)
# with open("/home/tarun/XFaaS/serwo/examples/NewQuantumWorkflow/reconstruction_out.json", "w") as f:
#   json.dump(obj, f)
# logging.info("Output object:"+str(body))