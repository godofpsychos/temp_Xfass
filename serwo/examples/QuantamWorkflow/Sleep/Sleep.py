from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging
import time
# import sys
# logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def user_function(xfaas_object) -> SerWOObject:
  try:
    logging.info("We are in the sleep fn")
    body=xfaas_object.get_body()
    time.sleep(body["time"])
    return xfaas_object
  except Exception as e:
    logging.info(e)
    logging.info(e)
    logging.info("Error in Sleep function")
    raise Exception("[SerWOLite-Error]::Error at user function",e)

# x={'job_id': 'cnldvmttjerd52himaog'}
# z=user_function(SerWOObject(body=x))
# print("Z's value:",z.get_body())