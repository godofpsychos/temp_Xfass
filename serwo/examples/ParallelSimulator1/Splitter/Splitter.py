import numpy as np
from numpy.lib.shape_base import kron
from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliList
from circuit_knitting.cutting import (
    OptimizationParameters,
    DeviceConstraints,
    find_cuts,
    cut_wires,
    expand_observables,
    partition_problem,
    generate_cutting_experiments
)
import json
from .qutils import marshaller, serializers
from qiskit.circuit.random import random_circuit
from python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging

def create_observables(qc: QuantumCircuit) -> list:
    observables = []
    for i in range(qc.num_qubits):
        obs = 'I'*(i)+'Z'+'I'*(qc.num_qubits-i-1)
        observables.append(obs)
    return observables

# def lambda_handler(event, context):
#     input = event['body']  
#     # The cut points are assumed to be marked already
#     circuit = serializers.circuit_deserializer(input['data']['circuit'])
#     observables = PauliList(input['data']['observables'])

#     # Specify settings for the cut-finding optimizer
#     optimization_settings = OptimizationParameters(seed=111)

#     # Specify the size of the QPUs available
#     device_constraints = DeviceConstraints(qubits_per_subcircuit=10)

#     cut_circuit, metadata = find_cuts(circuit, optimization_settings, device_constraints)

#     qc_w_ancilla = cut_wires(cut_circuit)
#     observables_expanded = expand_observables(observables, circuit, qc_w_ancilla)
#     partitioned_problem = partition_problem(circuit=qc_w_ancilla, observables=observables_expanded)
#     subobservables = partitioned_problem.subobservables
#     subexperiments, coefficients = generate_cutting_experiments(
#                                     circuits=partitioned_problem.subcircuits,
#                                     observables=subobservables,
#                                     num_samples=np.inf
#                                     )
#     print(subexperiments.keys())
#     data = {}
#     data['subexperiments'] = marshaller.jsonifyCuts(subexperiments=subexperiments)
#     data['subobservables'] = marshaller.sub_observables_to_dict(subobservables)
#     data['coefficients'] = marshaller.coefficients_to_list(coeffcients=coefficients)
#     return {
#         "statusCode": 200,
#         "body": {
#                 "data": data, \
#                 "credentials": input['credentials'], \
#                 "devices": input['devices']
#             }
#         }

def user_function(xfaas_object) -> SerWOObject:
    try:
        input = xfaas_object.get_body()
            # The cut points are assumed to be marked already
        circuit = serializers.circuit_deserializer(input['data']['circuit'])
        observables = PauliList(input['data']['observables'])

        # Specify settings for the cut-finding optimizer
        optimization_settings = OptimizationParameters(seed=111)

        # Specify the size of the QPUs available
        device_constraints = DeviceConstraints(qubits_per_subcircuit=10)

        cut_circuit, metadata = find_cuts(circuit, optimization_settings, device_constraints)

        qc_w_ancilla = cut_wires(cut_circuit)
        observables_expanded = expand_observables(observables, circuit, qc_w_ancilla)
        partitioned_problem = partition_problem(circuit=qc_w_ancilla, observables=observables_expanded)
        subobservables = partitioned_problem.subobservables
        subexperiments, coefficients = generate_cutting_experiments(
                                        circuits=partitioned_problem.subcircuits,
                                        observables=subobservables,
                                        num_samples=np.inf
                                        )
        print(subexperiments.keys())
        data = {}
        data['subexperiments'] = marshaller.jsonifyCuts(subexperiments=subexperiments)
        data['subobservables'] = marshaller.sub_observables_to_dict(subobservables)
        data['coefficients'] = marshaller.coefficients_to_list(coeffcients=coefficients)
               
        returnbody = {
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






# f=open("/home/tarun/XFaaS/serwo/examples/SerialSimulator/input-circuit.json")
# body=json.load(f)
# # body=json.loads(body)
# z=user_function(SerWOObject(body=body))
# body=z.get_body()
# obj=json.dumps(body,default=str)
# with open("/home/tarun/XFaaS/serwo/examples/SerialSimulator/splitter_out.json", "w") as f:
#   json.dump(obj, f)
# logging.info("Output object:"+str(body))