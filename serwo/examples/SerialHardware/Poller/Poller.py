# OM NAMO GANAPATHAYEN NAMAHA

import json
from qiskit_ibm_runtime import QiskitRuntimeService
from .qsserializers import program_serializers, serializers
from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging
from qiskit.providers.job import JobStatus

def user_function(xfaas_object) -> SerWOObject:
    try:
        input = xfaas_object.get_body()
        qtoken = input['credentials']['ibmq']['qtoken']
        service = QiskitRuntimeService(channel="ibm_quantum", token=qtoken)
        results = {}
        any_failed_job = False
        for job in input['jobs']:
            
            # completedJob = service.job(job_id=job['id'])
            # job = service.job(job_id=job['id'])
            # except Exception as e:
            #     print(f"Error while retrieving job {job['id']}: {str(e)}")
            #     completedJob = ''
                # any_failed_job = True
            logging.info("We are before job load:"+str(job['id']))
            completedJob = service.job(job_id=job['id'])
            logging.info("We are after job")
            # logging.info(str(completedJob))
            
            if completedJob.status() != JobStatus.DONE:
                completedJob = ''
                any_failed_job = True
            if completedJob != '':
                results[job['key']] = json.dumps(completedJob.result(), \
                                                cls=program_serializers.QiskitObjectsEncoder)

        if any_failed_job:
            # event['status'] = "AWAITED"
            input["Poll"]=True
            return SerWOObject(body=input)

        data = {}
        data['subobservables'] = input['data']['subobservables']
        data['results'] = results
        data['coefficients'] = input['data']['coefficients']
            
        
        
        returnbody= {
            "data": data, \
            "credentials": input['credentials'], \
            "devices": input['devices'],
            "Poll":False
        }
        
        return SerWOObject(body=returnbody)
    except Exception as e:
        print(e)
        logging.info(e)
        logging.info("Error in Poller function")
        raise Exception("[SerWOLite-Error]::Error at user function",e)