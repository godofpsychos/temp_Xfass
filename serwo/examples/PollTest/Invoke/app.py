from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging

def user_function(xfaas_object) -> SerWOObject:
    try:
        body = xfaas_object.get_body()
        val = int(body["user_val"])
        moddd = int(body["mod"])
        
        
        logging.info(str(body))
        logging.info("Invoke has been processed")
        return SerWOObject(body=body)
    except Exception as e:
        print(e)
        logging.info(e)
        logging.info("ERROR in poller function")
        raise Exception("[SerWOLite-Error]::Error at user function",e)

