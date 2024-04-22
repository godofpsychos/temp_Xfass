# OM NAMO GANAPATHAYEN NAMAHA
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_aer.primitives import Sampler
from qiskit_braket_provider  import BraketLocalBackend
from qutils import marshaller, program_serializers
import json
from qiskit_ibm_runtime import QiskitRuntimeService
from more_itertools import divide
import math
from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging


def user_function(xfaas_object) -> SerWOObject:
    try:
        input = xfaas_object.get_body()
        subexperiments = marshaller.objectifyCuts(input['data']['subexperiments'])
        qtoken = input['credentials']['ibmq']['qtoken']
        devices = input['devices']
        num_devices = len(devices)
        print(len(subexperiments), num_devices)
        batched_subexperiments = [list(b) for b in divide(num_devices, subexperiments.keys())]
        results = {}
        for i in range(num_devices):
            # device = devices[i]
            # if device['device'] != 'aer':
            #     break
            # if 'noise-model' in device:
            #     noise_model = NoiseModel.from_dict(device['noise-model'])
            #     sampler = Sampler(backend_options={"noise_model": noise_model})
            # elif 'backend' in device:
            #     service = QiskitRuntimeService(channel="ibm_quantum", token=qtoken)
            #     real_backend = service.backend(device['backend'])
            #     noise_model = NoiseModel.from_backend(real_backend)
            #     sampler = Sampler(backend_options={"noise_model": noise_model})
            # else:
            sampler = BraketLocalBackend()
            print(batched_subexperiments)
            for subexperiment_keys in batched_subexperiments[i]:
                for key in subexperiment_keys:
                    result = sampler.run(subexperiments[key]).result().results
                    # result=result.to_dict()
                    # print(type(result['backend_name']))
                    print(result)
                    results[key] = json.dumps(result)
                    # results[key] = json.dumps(result.to_dict())
        data = {}
        data['subobservables'] = input['data']['subobservables']
        data['results'] = results
        data['coefficients'] = input['data']['coefficients']
        returnbody={
            "data": data, \
            "credentials": input['credentials'], \
            "devices": input['devices']
        }
        return SerWOObject(body=returnbody)
    except Exception as e:
        print(e)
        logging.info(e)
        logging.info("Error in Invoke function")
        raise Exception("[SerWOLite-Error]::Error at user function",e)


# def test():
#     result = None
#     with open('../outputs/tmp.transpiler.json', 'r') as f:
#         data = json.load(f)
#         event = {'body': data['body']}
#         result = lambda_handler(event, None)
#     if result is not None:
#         with open('../outputs/tmp.simulator.json', 'w') as f:
#             json.dump(result, f)

f=open("/home/tarun/XFaaS/serwo/examples/SerialSimulatorAWS/transpiler_out.json")
body=json.load(f)
body=json.loads(body)
z=user_function(SerWOObject(body=body))
body=z.get_body()
obj=json.dumps(body,default=str)
with open("/home/tarun/XFaaS/serwo/examples/SerialSimulatorAWS/simulator_out.json", "w") as f:
  json.dump(obj, f)
logging.info("Output object:"+str(body))