# from .python.src.utils.classes.commons.serwo_objects import SerWOObject
import logging
import json
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Session, Options
from qiskit.providers.job import JobStatus
import sys
logging.basicConfig(stream=sys.stdout, level=logging.INFO)




class SerWOObject:
    def __init__(self, body=None, error=None, metadata=None) -> None:
        self._body = body
        self._err = error  # Either body might be set or error might be set
        self._metadata = metadata
        self._basepath = None

    def get_body(self):
        return self._body

    def get_metadata(self):
        return self._metadata

    def get_error(self, key):
        return self._err

    def get_basepath(self):
        return self._basepath

    def set_basepath(self, basepath):
        self._basepath = basepath

    def has_error(self):
        if self._err is not None:
            return True
        else:
            return False

    def to_json(self):
        return json.dumps(self.__dict__, default=lambda o: o.__dict__)

    @staticmethod
    def from_json(json_dct):
        return SerWOObject(json_dct["_body"], json_dct["_err"], json_dct["_metadata"])


class SerWOObjectsList:
    def __init__(self, body=None, metadata=None) -> None:
        self._object_list = []
        self._metadata = dict()
        if body:
            self._object_list.append(SerWOObject(body))
        if metadata:
            self._metadata = metadata
        self._basepath = None

    def get_objects(self):
        return self._object_list

    def get_metadata(self):
        return self._metadata

    def add_metadata(self, metadata):
        self._metadata = metadata

    # NOTE - will create issues if metadata is exposed to the user
    def add_object(self, body):
        self._object_list.append(SerWOObject(body))

    def get_basepath(self):
        return self._basepath

    def set_basepath(self, basepath):
        self._basepath = basepath


def build_serwo_list_object(event):
    """
    perform a union of all the metadata from incoming branches and
    collate into a metadata dictionary to remove duplicate data
    from a fan out at some point in the DAG
    """
    collated_metadata = dict()
    list_obj = SerWOObjectsList()
    functions_metadata_dict = dict()
    collated_functions_metadata_list = []
    for record in event:
        incoming_metadata = record.get("metadata")
        collated_metadata.update(
            dict(
                workflow_instance_id=incoming_metadata.get("workflow_instance_id"),
                workflow_start_time=incoming_metadata.get("workflow_start_time"),
                overheads=incoming_metadata.get("overheads"),
                request_timestamp=incoming_metadata.get("request_timestamp"),
                session_id=incoming_metadata.get("session_id"),
                deployment_id = incoming_metadata.get("deployment_id")
                # cpu = incoming_metadata.get("cpu")
            )
        )
        # get the functions list for each record and add it to a dict to remove duplicates
        functions_metadata_list = incoming_metadata.get("functions")
        for data in functions_metadata_list:
            for fid, fdata in data.items():
                functions_metadata_dict[fid] = fdata
        list_obj.add_object(body=record.get("body"))
    # convert the function metadata dict to a list to be added to collated metadata
    for fid, fdata in functions_metadata_dict.items():
        collated_functions_metadata_list.append({fid: fdata})
    collated_metadata.update(functions=collated_functions_metadata_list)
    # NOTE - remove the unnecesary serialisation
    list_obj.add_metadata(collated_metadata)
    return list_obj


def build_serwo_object(event):
    return SerWOObject(body=event["body"], metadata=event["metadata"])



def user_function(xfaas_object) -> SerWOObject:
  try:
    logging.info("We are in the fn")
    body=xfaas_object.get_body()
    # logging.info("Body:"+json.dumps(body))
    # logging.info("Job Id"+json.dumps(body["sub-experiments"]["0"]["id"]))
    Awaited_job_ids = body["Awaited_job_ids"]
    # logging.info("Job Id:"+str(job_ids))
    logging.info("We are in the fn line 1")
    service = QiskitRuntimeService(
    channel='ibm_quantum',
    instance='ibm-q/open/main',
    token='0657963f91c2cee472772a9e0829a5d37b3f303025acd176a077aa4de8fddfeb496e409e0221a1fc8b5ed75eef435efd974ba2811e5c69380422e5adab61c6eb'
)
    session = Session(service=service, backend='ibmq_qasm_simulator')
    Sucessful_job_id=[]
    Curr_Awaited_job_ids=[]
    output_body={}
    output_body["time"]=body["time"]
    if "Sucessful_job_id" in body:
      Sucessful_job_id=body["Sucessful_job_id"]
    for job_id in Awaited_job_ids:
      job = service.job(job_id=job_id)
      if job.status() == JobStatus.ERROR or job.status() == JobStatus.CANCELLED:
        #send it to failure
        output_body["message"]="Circuit Failure due to error or cancellation"
        output_body["Poll"]="No"
        return SerWOObject(body=output_body) 
      else:
        if job.status() == JobStatus.DONE:
          Sucessful_job_id.append({job_id:job.result()})
          # logging.info("Result of "+str(job_id)+ " : "+str(job.result()))

        else:
          Curr_Awaited_job_ids.append(job_id)
    
    if len(Curr_Awaited_job_ids)==0:
      output_body["message"]="All Quantam Jobs are executed Sucessfully"
      output_body["Poll"]="No"
      output_body["Sucessful_job_id"]= Sucessful_job_id
      # metadata=json.dumps({"status": "SUCCEEDED","statusCode": 200,})
      return SerWOObject(body=output_body)   
    else:
      output_body["message"]="Circuit Awaited"
      output_body["Poll"]="Yes"
      output_body["Awaited_job_ids"] = Curr_Awaited_job_ids
      output_body["Sucessful_job_id"]= Sucessful_job_id
      return SerWOObject(body=output_body)
  except Exception as e:
    logging.info(e)
    logging.info(e)
    logging.info("Error in Poll function")
    raise Exception("[SerWOLite-Error]::Error at user function",e)

x={'Awaited_job_ids': ['cnopqve4r64me7haaatg', 'cnopqvn9dnnkolqobcvg','cnoq9veui0m7nbqi8ipg','cnoq43oalmrcvvnjflpg','cnoostu4r64me7ha8gag'], 'time': 45}
z=user_function(SerWOObject(body=x))
print("Z's value:",z.get_body())