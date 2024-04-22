from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging

def user_function(xfaas_object) -> SerWOObject:
    try:
        body = xfaas_object.get_body()
        returnbody = body.copy()
        # returnbody(body)
        val = int(body["user_val"])
        # Incrementing the values
        returnbody["user_val"] = val 
        logging.info("Invoke Request has been processed")
        logging.info(returnbody)
        return SerWOObject(body=returnbody)
    except Exception as e:
        print(e)
        logging.info(e)
        logging.info("Error in Invoke function")
        raise Exception("[SerWOLite-Error]::Error at user function",e)
