import json
import numpy as np
from python.src.utils.classes.commons.serwo_objects import SerWOObject
from numpy.lib.shape_base import kron
from qiskit.circuit.library import EfficientSU2
from qiskit.quantum_info import PauliList
from circuit_knitting.cutting import partition_problem, generate_cutting_experiments
from .qsserializers import program_serializers, serializers
from qiskit_ibm_runtime import QiskitRuntimeService
import logging
# import sys
# logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def jsonifyCuts(subexperiments):
  jsonDict = {}
  l = []
  i = 0
  # numExp = len(subexperiments)
  for key in subexperiments.keys():
    if isinstance(subexperiments[key], list):
      lc = []
      for sc in subexperiments[key]:
        scStr = serializers.circuit_serializer(sc)
        lc.append(scStr)
    jsonStr = {'sub-circuits': lc, 'id': key}
    l.append(jsonStr)
  jsonDict['sub-experiments'] = l
  return json.dumps(jsonDict)



def user_function(xfaas_object) -> SerWOObject:
  try:
    logging.info("In the task A")
    qc = EfficientSU2(4, entanglement="linear", reps=2).decompose()
    logging.info("In the task A Line 1")
    qc.assign_parameters([0.4] * len(qc.parameters), inplace=True)
    logging.info("In the task A Line 2")
    observables = PauliList(["ZZII", "IZZI", "IIZZ", "XIXI", "ZIZZ", "IXIX"])
    logging.info("In the task A Line 3")
    partitioned_problem = partition_problem(
      circuit=qc, partition_labels="AABB", observables=observables
    )
    logging.info("In the task A Line 4") 
    subcircuits = partitioned_problem.subcircuits
    logging.info("In the task A Line 5")
    # logging.info(" subcircuits here"+json.dumps(subcircuits))
    subobservables = partitioned_problem.subobservables
    bases = partitioned_problem.bases
    # logging.info("In the task A Line 6")
    subexperiments, coefficients = generate_cutting_experiments(
    circuits=subcircuits,
    observables=subobservables,
      num_samples=np.inf
    )
    logging.info("In the task A Line 7")
    # logging.info("here"+json.dumps( subexperiments))
    serialized_subckts = jsonifyCuts(subexperiments=subexperiments)
    body=xfaas_object.get_body()
    retval = {
        "statusCode": 200,
        "body": {
                "circuits":{"serialized_subckts": serialized_subckts},
                 "time":body["time"],
                 "message":"Invocation and Subcircuit genration is completed sucessfully"
                }
    }
    # print("return val", retval)
    # return retval
    return SerWOObject(body=retval["body"])
  except Exception as e:
    logging.info(e)
    logging.info(e)
    logging.info("Error in Invoke function")
    raise Exception("[SerWOLite-Error]::Error at user function",e)
  
# z=user_function(SerWOObject(body={
#     "user_val": 1,
#     "mod": 10,
#     "str":"This is quantam payload1",
#     "time": 45
#   }))
# print("Output object:",json.dumps(z.get_body()))