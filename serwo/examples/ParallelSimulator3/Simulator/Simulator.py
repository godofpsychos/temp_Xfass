# OM NAMO GANAPATHAYEN NAMAHA
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_aer.primitives import Sampler
from .qutils import marshaller, program_serializers
import json
from qiskit_ibm_runtime import QiskitRuntimeService
# from more_itertools import divide
# import math
from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging

# def lambda_handler(event, context):
#     input = event['body']
#     subexperiments = marshaller.objectifyCuts(input['data']['subexperiments'])
#     qtoken = input['credentials']['ibmq']['qtoken']
#     devices = input['devices']
#     num_devices = len(devices)
#     batched_subexperiments = list(chunked(subexperiments, int(len(subexperiments) / num_devices)))
#     results = {}
#     for i in range(num_devices):
#         device = devices[i]
#         if device['device'] != 'aer':
#             break
#         if 'noise-model' in device:
#             noise_model = NoiseModel.from_dict(device['noise-model'])
#             sampler = Sampler(backend_options={"noise_model": noise_model})
#         elif 'backend' in device:
#             service = QiskitRuntimeService(channel="ibm_quantum", token=qtoken)
#             real_backend = service.backend(device['backend'])
#             noise_model = NoiseModel.from_backend(real_backend)
#             sampler = Sampler(backend_options={"noise_model": noise_model})
#         else:
#             sampler = Sampler()
#         for subexperiment_key in batched_subexperiments[i]:
#             key = subexperiment_key[0]
#             result = sampler.run(subexperiments[key]).result()
#             results[key] = json.dumps(result, cls=program_serializers.QiskitObjectsEncoder)
#     data = {}
#     data['subobservables'] = input['data']['subobservables']
#     data['results'] = results
#     data['coefficients'] = input['data']['coefficients']
#     return {
#         "statusCode": 200,
#         "body": {
#             "data": data, \
#             "credentials": input['credentials'], \
#             "devices": input['devices']
#         }
#     }
def user_function(xfaas_object) -> SerWOObject:
    try:
        input = xfaas_object.get_body()
        batch_of_subexperiments = marshaller.objectifyCuts(input['data']['batch']['subexperiments'])
        device_index = int(input['data']['batch']['index'])
        qtoken = input['credentials']['ibmq']['qtoken']
        devices = input['devices']
        results = {}
        device = devices[device_index]
        sampler = None
        if 'noise-model' in device:
            noise_model = NoiseModel.from_dict(device['noise-model'])
            sampler = Sampler(backend_options={"noise_model": noise_model})
        elif 'backend' in device:
            service = QiskitRuntimeService(channel="ibm_quantum", token=qtoken)
            real_backend = service.backend(device['backend'])
            noise_model = NoiseModel.from_backend(real_backend)
            sampler = Sampler(backend_options={"noise_model": noise_model})
        else:
            sampler = Sampler()
        for key, subexperiment in batch_of_subexperiments.items():
            result = sampler.run(subexperiment).result()
            results[key] = json.dumps(result, cls=program_serializers.QiskitObjectsEncoder)
        data = {}
        data['subobservables'] = input['data']['subobservables']
        data['batch'] = {'results': results, 'index': device_index}
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

# f=open("/home/tarun/XFaaS/serwo/examples/SerialSimulator/transpiler_out.json")
# body=json.load(f)
# body=json.loads(body)
# z=user_function(SerWOObject(body=body))
# body=z.get_body()
# obj=json.dumps(body,default=str)
# with open("/home/tarun/XFaaS/serwo/examples/SerialSimulator/simulator_out.json", "w") as f:
#   json.dump(obj, f)
# logging.info("Output object:"+str(body))