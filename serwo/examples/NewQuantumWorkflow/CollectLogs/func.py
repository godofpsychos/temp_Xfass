from azure.storage.queue import QueueClient
import json
from python.src.utils.classes.commons.serwo_objects import SerWOObject
import os, uuid


connect_str = 'DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName=xfaaslogcentralindia;AccountKey=eTeexxyEMZLDZnf3Em+9pY9JeB/XPwqfTPvXfQjrl08c2fNai2pT1jqPoDJVTHqb66HZhesYyqb4+ASt1naAkA==;BlobEndpoint=https://xfaaslogcentralindia.blob.core.windows.net/;FileEndpoint=https://xfaaslogcentralindia.file.core.windows.net/;QueueEndpoint=https://xfaaslogcentralindia.queue.core.windows.net/;TableEndpoint=https://xfaaslogcentralindia.table.core.windows.net/'
queue_name = 'karjc'

queue = QueueClient.from_connection_string(conn_str=connect_str, queue_name=queue_name)


def user_function(serwoObject) -> SerWOObject:
    try:
        fin_dict = dict()
        data = serwoObject.get_body()
        print("Data to push - ", data)
        metadata = serwoObject.get_metadata()
        fin_dict["data"] = "success: OK"
        fin_dict["metadata"] = metadata
        print("Fin dict - ", fin_dict)
        queue.send_message(json.dumps(fin_dict))
        data = {"body": "success: OK"}
        return SerWOObject(body=data)
    except Exception as e:
        return SerWOObject(error=True)
