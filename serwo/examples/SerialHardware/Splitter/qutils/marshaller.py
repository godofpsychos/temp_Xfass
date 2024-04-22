# OM NAMO GANAPATHAYEN NAMAHA
from . import serializers, program_serializers
import json
from qiskit.quantum_info import PauliList


def jsonifyCuts(subexperiments):
    jsonDict = {}
    for key, items in subexperiments.items():
        print(key, len(items))
        l = []
        for item in items:
            l.append(serializers.circuit_serializer(item))
        jsonDict[key] = l
    return json.dumps(jsonDict)

def objectifyCuts(data):
    jsonData = json.loads(data)
    objData = {}
    for key, items in jsonData.items():
        objData[key] = [serializers.circuit_deserializer(item) for item in items]
    return objData

def objectify_specific(data, index):
    data_as_dict = json.loads(data)
    serialized_sub_experiments = data_as_dict['sub-experiments']
    sub_experiment_serialized = serialized_sub_experiments[index]
    sub_experiment = serializers.circuit_deserializer(sub_experiment_serialized)
    return sub_experiment

def coefficients_to_list(coeffcients):
    l = []
    for c in coeffcients:
        l.append((c[0], int(c[1].value)))
    return json.dumps(l)

# def json2coefficients(jsonData):
#     return json.loads(jsonData)

def sub_observables_to_dict(subobservables):
    d = {}
    for k, pauilist in subobservables.items():
        d[k] = pauilist.to_labels()
    return d

def dict_to_sub_observables(data):
    output_d = {}
    for k, pauilist_str in data.items():
        output_d[int(k)] = PauliList(pauilist_str)
    return output_d

def decode_results(results):
    decoded_results = {}
    for key, result in results.items():
        decoded_result = json.loads(result, cls=program_serializers.QiskitObjectsDecoder)
        for i in range(len(decoded_result.quasi_dists)):
            decoded_result.quasi_dists[i] = fix_quasidist(decoded_result.quasi_dists[i])
        decoded_results[int(key)] = decoded_result
    return decoded_results

def fix_quasidist(data):
    di = {}
    for k, v in data.items():
        ki = int(k)
        di[ki] = v
    return di