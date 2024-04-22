from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from .qutils import marshaller
from more_itertools import divide
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
import json
from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging
 
# def lambda_handler(event, context):
#     input = event['body']
#     qtoken = input['credentials']['ibmq']['qtoken']
#     service = QiskitRuntimeService('ibm_quantum', token=qtoken)
#     devices = input['devices']
#     num_devices = len(devices)
#     subexperiments = marshaller.objectifyCuts(input['data']['subexperiments'])
#     batched_subexperiments = list(chunked(subexperiments.keys(), int(len(subexperiments.keys())/ num_devices)))
#     subexperiments_transpiled = {}
#     for i in range(num_devices):
#         device = devices[i]
#         skip_transpilation = False
#         if device['device'] == 'aer':
#             if 'backend' in device:
#                 real_backend = service.backend(device['backend'])
#                 backend = AerSimulator.from_backend(real_backend)
#             elif 'noise-model' in device:
#                 noise_model = NoiseModel.from_dict(device['noise-model'])
#                 backend = AerSimulator(noise_model=noise_model)
#         elif device['device'] == 'ibmq_qasm_simulator':
#             skip_transpilation = True
#             break
#         else:
#             backend = service.backend(device['backend'])
#     if not skip_transpilation:
#         pm = generate_preset_pass_manager(2, backend)
#         for subexperiment_key in batched_subexperiments[i]:
#             key = subexperiment_key[0]
#             l = []
#             for subcircuit in subexperiments[key]:
#                 l.append(pm.run(subcircuit))
#             subexperiments_transpiled[key] = l
#     if len(subexperiments_transpiled) == 0:
#         subexperiments_transpiled = subexperiments
#     data = input['data']
#     data['subexperiments'] = marshaller.jsonifyCuts(subexperiments=subexperiments_transpiled)
#     return {
#         "statusCode": 200,
#         "body": {
#             "data": data, \
#             "credentials": input['credentials'], \
#             "devices": input['devices']
#         }
#     }
        # qtoken = input['credentials']['ibmq']['qtoken']
        # service = QiskitRuntimeService('ibm_quantum', token=qtoken)
        # devices = input['devices']
        # num_devices = len(devices)
        # subexperiments = marshaller.objectifyCuts(input['data']['subexperiments'])
        # batched_subexperiments = list(chunked(subexperiments.keys(), int(len(subexperiments.keys())/ num_devices)))
        # subexperiments_transpiled = {}
        # backend = None
        # for i in range(num_devices):
        #     device = devices[i]
        #     skip_transpilation = False
        #     if device['device'] == 'aer':
        #         if 'backend' in device:
        #             real_backend = service.backend(device['backend'])
        #             backend = AerSimulator.from_backend(real_backend)
        #         elif 'noise-model' in device:
        #             noise_model = NoiseModel.from_dict(device['noise-model'])
        #             backend = AerSimulator(noise_model=noise_model)
        #         elif 'backend' not in device:
        #             skip_transpilation = True
        #             break
        #     elif device['device'] == 'ibmq_qasm_simulator':
        #         skip_transpilation = True
        #         break
        #     else:
        #         backend = service.backend(device['backend'])
        # if not skip_transpilation:
        #     pm = generate_preset_pass_manager(2, backend)
        #     for subexperiment_key in batched_subexperiments[i]:
        #         key = subexperiment_key[0]
        #         l = []
        #         for subcircuit in subexperiments[key]:
        #             l.append(pm.run(subcircuit))
        #         subexperiments_transpiled[key] = l
        # if len(subexperiments_transpiled) == 0:
        #     subexperiments_transpiled = subexperiments
        # data = input['data']
        # data['subexperiments'] = marshaller.jsonifyCuts(subexperiments=subexperiments_transpiled)
def user_function(xfaas_object) -> SerWOObject:
    try:
        input = xfaas_object.get_body()
        # print(input)
        qtoken = input['credentials']['ibmq']['qtoken']
        service = QiskitRuntimeService('ibm_quantum', token=qtoken)
        devices = input['devices']
        num_devices = len(devices)
        device_index = int('5')
        subexperiments = marshaller.objectifyCuts(input['data']['subexperiments'])
        batched_subexperiments = [list(b) for b in divide(num_devices, subexperiments.keys())]
        subexperiments_transpiled = {}
        device = devices[device_index]
        skip_transpilation = False
        if device['device'] == 'aer':
            if 'backend' in device:
                real_backend = service.backend(device['backend'])
                backend = AerSimulator.from_backend(real_backend)
            elif 'noise-model' in device:
                noise_model = NoiseModel.from_dict(device['noise-model'])
                backend = AerSimulator(noise_model=noise_model)
            else:
                skip_transpilation = True
        elif device['device'] == 'ibmq_qasm_simulator':
            skip_transpilation = True
        else:
            backend = service.get_backend(device)
        if not skip_transpilation:
            pm = generate_preset_pass_manager(2, backend)
            for subexperiment_keys in batched_subexperiments[device_index]:
                for key in subexperiment_keys:
                    l = []
                    for subcircuit in subexperiments[key]:
                        l.append(pm.run(subcircuit))
                    subexperiments_transpiled[key] = l
        if len(subexperiments_transpiled) == 0:
            subexperiments_transpiled = subexperiments
        data = input['data']
        data['batch'] = {'subexperiments': marshaller.jsonifyCuts(subexperiments=subexperiments_transpiled), \
                        'index': device_index}
 
        returnbody ={
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
 
 
 
# f=open("/home/tarun/XFaaS/serwo/examples/SerialSimulator/splitter_out.json")
# body=json.load(f)
# body=json.loads(body)
# z=user_function(SerWOObject(body=body))
# body=z.get_body()
# obj=json.dumps(body,default=str)
# with open("/home/tarun/XFaaS/serwo/examples/SerialSimulator/transpiler_out.json", "w") as f:
#   json.dump(obj, f)
# logging.info("Output object:"+str(body))