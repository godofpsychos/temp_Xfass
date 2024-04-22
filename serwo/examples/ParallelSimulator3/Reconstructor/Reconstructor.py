# OM NAMO GANAPATHAYEN NAMAHA
from circuit_knitting.cutting import reconstruct_expectation_values
from .qutils import marshaller, program_serializers
import json
from .python.src.utils.classes.commons.serwo_objects import SerWOObject,SerWOObjectsList
import logging

# def lambda_handler(event, context):
#     input = event['body']
#     subobservables = marshaller.dict_to_sub_observables(input['data']['subobservables'])
#     coefficients = json.loads(input['data']['coefficients'])
#     corrected_coefficients = []
#     for c in coefficients:
#         corrected_coefficients.append(tuple(c))
#     results = marshaller.decode_results(input['data']['results'])
#     reconstructed_expvals = reconstruct_expectation_values(
#         results,
#         corrected_coefficients,
#         subobservables,
#     )
#     print(reconstructed_expvals)
#     return {
#         "statusCode": 200,
#         "body": {
#                 "data": {'result': reconstructed_expvals}, \
#                 "devices": input['devices']
#             }
#         }

def user_function(xfaas_object) -> SerWOObject:
    try:
        subobservables = None
        corrected_coefficients = None
        batches = []
        Serwo_list=xfaas_object.get_objects()
        for obj in Serwo_list:
            input = obj.get_body()
            if subobservables is None:
                subobservables = marshaller.dict_to_sub_observables(input['data']['subobservables'])
            if corrected_coefficients is None:
                coefficients = json.loads(input['data']['coefficients'])
                corrected_coefficients = []
                for c in coefficients:
                    corrected_coefficients.append(tuple(c))
            batches.append(input['data']['batch'])
        # batches = input['batches']
        results = {}
        for batch in batches:
            batch_result = marshaller.decode_results(batch['results'])
            results.update(batch_result)
        reconstructed_expvals = reconstruct_expectation_values(
            results,
            corrected_coefficients,
            subobservables,
        )
        print(reconstructed_expvals)

        returnbody = {
                "data": {'result': reconstructed_expvals}
            }
        return SerWOObject(body=returnbody)
    except Exception as e:
        print(e)
        logging.info(e)
        logging.info("Error in Invoke function")
        raise Exception("[SerWOLite-Error]::Error at user function",e)



# f=open("/home/tarun/XFaaS/serwo/examples/SerialSimulator/simulator_out.json")
# body=json.load(f)
# body=json.loads(body)
# z=user_function(SerWOObject(body=body))
# body=z.get_body()
# obj=json.dumps(body,default=str)
# with open("/home/tarun/XFaaS/serwo/examples/SerialSimulator/reconstructor_out.json", "w") as f:
#   json.dump(obj, f)
# logging.info("Output object:"+str(body))