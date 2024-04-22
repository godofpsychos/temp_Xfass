from result_analysis_script import result_analysis 

url_list=[('https://xfaasibmserialhardware938577.azurewebsites.net/runtime/webhooks/durabletask/instances/fecd15ad6d8b4f19a6fd18a3283f77b0?taskHub=xfaasIBMSerialHardware938577&connection=Storage&code=p274sbXJxG3SmBBuhKLlgQrhKog7p8Yzgm_Rd_Syw5NZAzFucfKksA==','serwo/examples/SerialHardware'), ('https://xfaasibmserialhardware938577.azurewebsites.net/runtime/webhooks/durabletask/instances/22d08e68e4054e3ca9ae1716e34b99b3?taskHub=xfaasIBMSerialHardware938577&connection=Storage&code=p274sbXJxG3SmBBuhKLlgQrhKog7p8Yzgm_Rd_Syw5NZAzFucfKksA==','serwo/examples/SerialHardware')]

result_analysis.data_analysis(url_list)

# import matplotlib.pyplot as plt
# from braket.circuits import Circuit
# from qiskit_braket_provider  import BraketLocalBackend
# import json
# from qutils import marshaller, serializers
# from braket.devices import StateVectorSimulator





# Define custom quantum circuit
# custom_circuit = "eJy9Vz1PwlAUfe/1g5YaEzdWF8UYBuPkhIkoASc+BuJmsBhcFINGgyYO7kzO/gN/ArA5aIy/wLj6AzQaYpTioyAB0nsv7Rt6m9Dzzul59x7STCq3ncpbnAn2t7hdYVaJGZ3bGdZfzs9c3h8Uy8fFk3I1trK2Gj9r7D/dRlntssK7EM4r7P/iA1s4S5FVlVWTVZc1JKshqylrWFbL3bn3pGCj1+ZGNrlbtbuCKl0lutTDxyCyOy6g1JPxUG+fJ561litwHDhXcMEookgskW/Pmy0AmLvg64i9dzH31YSYwvFaZ+2tzGItAFNec9H3w4WPptsm48AuD+SU+ZD5aP8mKZuaBX4TNe6/T4+WxHpgXnsHi9FTMklk3w1BI4J2hID4B9hcOBcF9S6IDCOa5h2skDJMwWtFZBiOCJ5hkFNWSBk24N8kZVOzwG8ieIYpYLtUCEJ1LhrgXVTK1KooIsTUaqSp1fBaEVOLI4JPLeSUNdLUDvg3SdnULPCbCD61RK+9v5AOINKHieLgQ9X9sWCEssAs8A4ODYHfQENhkLX63xcFUV9+efyEEQE8COGlXd2lY+nkTVCN0fm38dzpIUIPwYKV4F/wg+WLfwblM82kfKaZNCJoUpje/TMAysKkDLOoRoAyDEeEyDAT4kEYLw2RYcSu89xDYUIPwTKM4B8iw4hEAP8Y+xlYvQd+AcaAApo="
# f=open("/home/tarun/XFaaS/serwo/examples/SerialSimulatorAWS/transpiler_out.json")
# body = json.load(f)
# input = json.loads(body)
# subexperiments = marshaller.objectifyCuts(input['data']['subexperiments'])
# num_devices = 1
# print(len(subexperiments), num_devices)
# batched_subexperiments = [list(b) for b in divide(num_devices, subexperiments.keys())]
# results = {}
# print(subexperiments)
# Submit the circuit to the local simulator
# custom_circuit=serializers.circuit_deserializer('eJy9mD1Lw0Acxu8ur6UiOunq4gvSwUXcFKyKioNth+IibXqK4Fv6BlIFB3cnv4YfQd0cdPATiKsfQFGKaC9N01iTmv9dkoP0QrjfPU+e3P9KsrmaXV/NJTHCqN0wNVFyB+mt04R9sEZah2yfF4y9slHbq6ZmZufsS6hxZiJrOMHmDPrdsGsO1iS778yn2L1q95rd6yYjB1q8GdaM3z7NwJb5EXxUrNByvVDcp9sHtFCplekBPaxWwtI32uQQNo9L3gKdoQR5t6XFzEqhSq1ETMuKahvCPkRmywF2Oj4eLpsn6SflznHoB2fzDswlNJpK55pjiTsAjB34YpSWToc/byGhYH6vg3R5c6IRQygv2cm3o/H3W2ed+MGODuQp457wufPr5yy0CKIWurn/qh9PkYXYsg4OE+8q6WeymwYRE4KuCALJDzA5YT8S171w7GGCoQWHJaE9TOL3yrGH8QnB9zDIU5aE9jBXfv2chRZB1ELwPUwCxyVDCJn9KIB7kUWqVuYS4qhaRahqFX6vHFXLJwSvWshTVoSq1pVfP2ehRRC1ELxqBbMOfkMqQEjtFZoHP1Q1mgg8nMUWQXBY64FfQUWhC3uNfl3kyeX08+MHTAiQgcZv7fx6LbW2chXXwmj92wRe6ZrAGoJtrAL5xV9YkeSn/83vP52swzpR+w4t7XYHB/YPGuq24DV8o/0pyXr1NawrAAIbyP3WFoAgjCAQQmKEBCFkRsgQQmGEAiFURqgQQmOEBiF0RrDPqe7vjZ1xP8kj8xM=')
# print(type(custom_circuit))
# device = BraketLocalBackend()
# task = device.run(custom_circuit,shots=1000)

# Print results after reconstruction
# result = task.result()
# print(type(result))
# print(result.results)
# counts = result.get_counts()
# print("Measurement Counts:", counts)
# plot_histogram(counts)
# state_vector = result.values[0].state_vector

# Print the state vector
# print("State Vector:", state_vector)

# Plot the histogram of measurement results
# plt.bar(counts.keys(), counts.values())
# plt.xlabel('Result')
# plt.ylabel('Count')
# plt.title('Measurement Results')
# plt.show()
