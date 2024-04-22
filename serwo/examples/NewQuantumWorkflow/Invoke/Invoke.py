from python.src.utils.classes.commons.serwo_objects import SerWOObject
from qiskit.circuit.library import EfficientSU2
from .qsserializers import  serializers
import logging
# import sys
# logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def user_function(xfaas_object) -> SerWOObject:
  try:
    logging.info("We are in  fn line 1")
    qc = EfficientSU2(4, entanglement="linear", reps=2).decompose()
    logging.info("We are in  fn line 2")
    qc.assign_parameters([0.4] * len(qc.parameters), inplace=True)
    scStr = serializers.circuit_serializer(qc)
    logging.info("We are in  fn line 3")
    logging.info(scStr)
    body=xfaas_object.get_body()
    body["circuit"]=scStr
    body["message"]="Invocation completed sucessfully"
    logging.info("We are in  fn line 4")
    return SerWOObject(body=body)
  except Exception as e:
    logging.info(e)
    logging.info(e)
    logging.info("Error in Invoke function")
    raise Exception("[SerWOLite-Error]::Error at user function",e)
  
# z=user_function(SerWOObject(body={
#     "message":"This is quantam payload",
#     "time": 45
#   }))
# body=z.get_body()
# # localStorage.setItem("Invoke_out", json.dumps(body))
# logging.info("Output object:"+str(body))