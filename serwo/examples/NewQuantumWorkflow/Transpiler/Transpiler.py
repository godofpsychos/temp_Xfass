import numpy as np
from numpy.lib.shape_base import kron
from qiskit.circuit.library import EfficientSU2
from qiskit.quantum_info import PauliList
from circuit_knitting.cutting import partition_problem, generate_cutting_experiments
from qsserializers import  serializers,QiskitObjectsEncoder
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from python.src.utils.classes.commons.serwo_objects import SerWOObject
from enum import Enum
import logging
import json
import sys
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def observable_dict_sterilizer(dict):
  for key in dict:
    var= dict[key]
    dict[key]= var.to_labels()
  return dict

def experiment_list_strilizer(dict):
  n_dict={}
  for key in dict:
    list=[]
    exp_list =dict[key]
    for subex in exp_list:
      list.append(serializers.circuit_serializer(subex))
      n_dict[key]=list
  return n_dict   

class WeightType(Enum):
    EXACT = 1
    SAMPLED = 2
def serialize_enum(enum_obj):
    return enum_obj.name

# Deserialization function to convert string to enum object
def deserialize_enum(enum_str):
    return WeightType[enum_str]

def sterilize_enum_list(list):
  n_list=[]
  for obj in list:
    a,b=obj
    b=serialize_enum(b)
    n_list.append((a,b))
  # print("sterilize_enum_list",n_list)
  return n_list  

def user_function(xfaas_object) -> SerWOObject:
  try:
    logging.info("We are in  fn line 1")
    body=xfaas_object.get_body()
    circuit=body["circuit"]
    qc = serializers.circuit_deserializer(circuit)
    observables = PauliList(["ZZII", "IZZI", "IIZZ", "XIXI", "ZIZZ", "IXIX"])
    logging.info("We are in  fn line 2")
    partitioned_problem = partition_problem(
        circuit=qc, partition_labels="AABB", observables=observables
    )
    subcircuits = partitioned_problem.subcircuits
    logging.info("printing subcircuits:"+ str(subcircuits))
    subobservables = partitioned_problem.subobservables
    # bases = partitioned_problem.bases
    logging.info("We are in  fn line 3")
    subexperiments, coefficients = generate_cutting_experiments(
      circuits=subcircuits,
      observables=subobservables,
      num_samples=np.inf
    )
    # print("subexperiments", subexperiments)
    subobservables=observable_dict_sterilizer(subobservables)
    # print("subobservables:",subobservables)
    # print("coefficients:",coefficients)

    logging.info("== transpilation start == ")
    service = QiskitRuntimeService(channel='ibm_quantum',instance='ibm-q/open/main',token='0657963f91c2cee472772a9e0829a5d37b3f303025acd176a077aa4de8fddfeb496e409e0221a1fc8b5ed75eef435efd974ba2811e5c69380422e5adab61c6eb')   
    backend = service.get_backend(body['backend'])
    pm = generate_preset_pass_manager(2, backend)
    subexperiments_trans = {}
    for key, subckt in subexperiments.items():
        subexperiments_trans[key] = pm.run(subckt)
    logging.info("Sub-Experiments:"+str(subexperiments_trans))
    logging.info("== transpilation end == ")

    body["coefficients"]= sterilize_enum_list(coefficients)
    body["subobservables"]=subobservables
    body["Transpiled_Subexperiment"]=experiment_list_strilizer(subexperiments_trans)
    body["message"]="Transpilation completed sucessfully"
    logging.info("We are in  fn line 4")
    return SerWOObject(body=body)
  except Exception as e:
    logging.info(e)
    logging.info(e)
    logging.info("Error in Invoke function")
    raise Exception("[SerWOLite-Error]::Error at user function",e)





# body= { 'message': 'Invocation completed sucessfully', 'time': 45, "backend":"ibm_brisbane",'circuit': 'eJwL9Az29gzhZmSAAcbUQgaeNAYOIJOFAQGYQFJQtpxrWlpmcmZqXklwqBFMQXVtISNYDyNjIQMqYEQyAwSY4TJsUFlGBuwgKNI9sSQVbF4aVIhj1kwQuGlPWHMUJZrhNjNSYjMOzSDAhKkPbKZzBNzZYBOGRCAxUWIzDs0gQDiQwKmNaTQ+MZxKUXwyU2IzDs0gQDiQmMAmjCY9DKeSo3k0PgcykBgY/iMBmBYAoCbiPA=='}
# z=user_function(SerWOObject(body=body))
# body=z.get_body()
# obj=json.dumps(body)
# with open("/home/tarun/XFaaS/serwo/examples/NewQuantumWorkflow/transpiler_out.json", "w") as f:
#     json.dump(obj, f)
# logging.info("Output object:"+str(body))