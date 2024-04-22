from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging

def user_function(xfaas_object) -> SerWOObject:
    try:
        body = xfaas_object.get_body()
        val = int(body["user_val"]) + 1
        moddd = int(body["mod"])
        body["after_mod"] = val % moddd
        # returnbody = body
        # if val%mod != 0:
        #     print("Calling invoke funtion...!!!")
        #     invoke()
        # else: 
        #     print("Request has been processed")
        logging.info(body)
        logging.info("Poll Workflow has been processed")
        return SerWOObject(body=body)
    except Exception as e:
        print(e)
        logging.info(e)
        logging.info("ERROR in poller function")
        raise Exception("[SerWOLite-Error]::Error at user function",e)

