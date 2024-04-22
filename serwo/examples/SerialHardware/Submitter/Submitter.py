from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Session, Options
from .qutils import marshaller
import math
from more_itertools import divide
from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging


def user_function(xfaas_object) -> SerWOObject:
    try:
        input = xfaas_object.get_body()
        subexperiments = marshaller.objectifyCuts(input['data']['subexperiments'])
        qtoken = input['credentials']['ibmq']['qtoken']
        service = QiskitRuntimeService(channel="ibm_quantum", token=qtoken)
        devices = input['devices']
        num_devices = len(devices)
        batched_subexperiments = [list(b) for b in divide(num_devices, subexperiments.keys())]
        options = Options()
        options.execution.shots = 1000 # {{ shots }}
        options.transpilation.skip_transpilation = True
        options.resilience_level = 1 # {{ resilience_level }} # set to 1 if you need measurement error mitigation
        jobs = []
        for i in range(num_devices):
            session = Session(service=service, backend=devices[i]['device'])
            sampler = Sampler(session=session, options=options)
            for key in batched_subexperiments[i]:
                job = sampler.run(subexperiments[key])
                jobs.append({'id': job.job_id(), 'key': key, 'device': devices[i]['device']})

        data = {}
        data["jobs"] = jobs
        data["data"] = input["data"]
        data["credentials"] = input["credentials"]    
        data["devices"]=devices
        
        returnbody=data
        return SerWOObject(body=returnbody)
    except Exception as e:
        print(e)
        logging.info(e)
        logging.info("Error in Submitter function")
        raise Exception("[SerWOLite-Error]::Error at user function",e)
