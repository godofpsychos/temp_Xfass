import matplotlib.pyplot as plt
import matplotlib.ticker as tck
import sys
import os
import json
import numpy as np
import networkx as nx
import pathlib
import pprint
import argparse
import statistics
import get_aws_containers as aws_containers

from typing import Any
from collections import defaultdict
from matplotlib.lines import lineStyles
from azure.storage.queue import QueueClient
from python.src.utils.classes.commons.logger import LoggerFactory

logger = LoggerFactory.get_logger(__file__, log_level="INFO")

class XFBenchPlotter:
    '''
    These are base parameters for the plt globally applied in case you explictly don't set anything
    via fontdicts etc.
    These will be used by default - you can add your customizations via code to override this
    '''
    # plt.rcParams["text.usetex"] = True
    # plt.rcParams["font.family"] = "serif"
    # plt.rcParams["font.serif"] = ["Computer Modern"]
    plt.rcParams['ytick.labelsize'] = 20
    plt.rcParams['xtick.labelsize'] = 20
    plt.rcParams['axes.titlesize'] = 20
    plt.rcParams['axes.labelsize'] = 20
    plt.rcParams['legend.fontsize'] = 20
    
    def __init__(self, workflow_directory: str, workflow_deployment_id: str, run_id: str, format: str):
        self.__workflow_directory = workflow_directory
        self.__workflow_deployment_id = workflow_deployment_id
        self.__run_id = run_id
        self.__xfaas_dag = self.__init__dag(self.__workflow_directory+ "/dag.json")
        self.__format = format
        '''
        Constructed directories and paths
        '''
        self.__exp_directory = pathlib.Path(self.__workflow_directory) / self.__workflow_deployment_id / self.__run_id
        self.__artifacts_filepath = self.__exp_directory / "artifact.json"
        self.__logs_dir = self.__exp_directory / "logs"
        self.__plots_dir = self.__exp_directory / "plots"

        # Create the logs and the plots directory
        if not os.path.exists(self.__logs_dir):
            os.makedirs(self.__logs_dir)

        if not os.path.exists(self.__plots_dir):
            os.makedirs(self.__plots_dir)

        '''
        Using provenance artifacts to construct the experiment configuration
        '''
        if not os.path.exists(self.__artifacts_filepath):
            raise FileNotFoundError(f"artifact.json Not Found under {self.__exp_directory}")
        
        '''
        Construct the experiment configuration from the artifacts
        '''
        with open(self.__artifacts_filepath, "r") as file:
            config = json.load(file)
        
        
        # TODO - create a function which generate the step_x and step_y from the exp_config
        self.__exp_conf = config.get("experiment_conf")
        self.__queue_name = config.get("queue_details").get("queue_name")
        self.__conn_str = config.get("queue_details").get("connection_string")
        self.__app_name = config.get("app_name")
        
        '''
        Create an experiment description dictionary
        '''
        temp_conf = list(self.__exp_conf.values())[0]
        self.__exp_desc = dict(wf_name=temp_conf.get("wf_name"),
                               csp=temp_conf.get("csp"),
                               dynamism=temp_conf.get("dynamism"),
                               payload=temp_conf.get("payload_size"),
                               rps = temp_conf.get("rps"))
        

        self.__logfile = f"{self.__get_outfile_prefix()}_dyndb_items.jsonl"

        '''
        Get the data from the queue and push to the file
        NOTE - if you call this again and logfile exists then it won't pull from queue
        '''
        if not os.path.exists(self.__logs_dir / self.__logfile):
            self.__get_from_queue_add_to_file()


    def __init__dag( self,user_config_path):
        def __load_user_spec( user_config_path):
            with open(user_config_path, "r") as user_dag_spec:
                dag_data = json.load(user_dag_spec)
            return dag_data
        __dag_config_data = dict() # dag configuration (picked up from user file)
        __nodeIDMap = {} # map: nodeName -> nodeId (used internally)
        __dag = nx.DiGraph() # networkx directed graph
        
        # throw an exception if loading file has a problem
        try:
            __dag_config_data = __load_user_spec(user_config_path)
            __workflow_name = __dag_config_data["WorkflowName"]
        except Exception as e:
            raise e
    
        index = 1
        for node in __dag_config_data["Nodes"]:
            nodeID = node["NodeId"]
            # TODO - add a better way to add node codenames to the DAG
            __nodeIDMap[node["NodeName"]] = nodeID
            __dag.add_node(nodeID,
                                NodeId=nodeID,
                                NodeName=node["NodeName"], 
                                Path=node["Path"],
                                EntryPoint=node["EntryPoint"],
                                MemoryInMB=node["MemoryInMB"],
                                Codename=node["Code"])
            index += 1

        # add edges in the dag
        for edge in __dag_config_data["Edges"]:
            for key in edge:
                for val in edge[key]:
                    __dag.add_edge(__nodeIDMap[key], __nodeIDMap[val])

        return __dag
        
    
    def __get_outfile_prefix(self):
        
        prefix = f"{self.__exp_desc.get('wf_name')}_{self.__exp_desc.get('csp')}_{self.__exp_desc.get('dynamism')}_{self.__exp_desc.get('payload')}"
        
        return prefix


    def __create_dynamo_db_items(self):
        print("Creating DynamoDB items")
        dynamodb_item_list = []

        queue = QueueClient.from_connection_string(conn_str=self.__conn_str, queue_name=self.__queue_name)
        response = queue.receive_messages(visibility_timeout=3000)
        print('Reading Queue')
        for message in response:
            queue_item = json.loads(message.content)
            metadata = queue_item["metadata"]
            
            # Filtering based on workflow deployment id during creation itself
            if metadata["deployment_id"].strip() == self.__workflow_deployment_id:
                dynamo_item = {}
                invocation_id = f"{metadata['workflow_instance_id']}-{metadata['session_id']}"
                dynamo_item["workflow_deployment_id"] = metadata["deployment_id"]
                dynamo_item["workflow_invocation_id"] = invocation_id
                dynamo_item["client_request_time_ms"] = str(
                    metadata["request_timestamp"]
                )
                dynamo_item["invocation_start_time_ms"] = str(
                    metadata["workflow_start_time"]
                )

                # add session id to dynamo db
                dynamo_item["session_id"] = str(metadata["session_id"])

                dynamo_item["functions"] = {}
                for item in metadata["functions"]:
                    for key in item.keys():
                        dynamo_item["functions"][key] = item[key]

                dynamodb_item_list.append(dynamo_item)

        return dynamodb_item_list
    
    '''
    Items written to the logfile are sorted w.r.t the client_request_time_ms
    '''
    def __get_from_queue_add_to_file(self):
        logger.info(f"Getting Items from Queue - {self.__queue_name}")
        sorted_dynamo_items = sorted(self.__create_dynamo_db_items(), key=lambda x: int(x["client_request_time_ms"]))
        with open(self.__logs_dir / self.__logfile, "w") as file:
            for dynamo_item in sorted_dynamo_items:
                dynamo_item_string = json.dumps(dynamo_item) + "\n"
                file.write(dynamo_item_string)


    def __get_provenance_logs(self):
        logger.info(f"Reading logfile {self.__logfile}")
        with open(self.__logs_dir / self.__logfile, "r") as file:
            loglines = [json.loads(line) for line in file.readlines()]
        return loglines
    
    '''
    Give the e2e time in seconds
    '''
    def __get_e2e_time(self, log_items):
        e2e_time = [] 
        sink_node = [node for node in self.__xfaas_dag.nodes if self.__xfaas_dag.out_degree(node) == 0][0]
        for item in log_items:
            e2e_time.append(int(item["functions"][sink_node]["end_delta"])/1000) # e2e time in seconds
        return e2e_time
    
    def __get_overheads(self, log_items):
        oh = [] 
        for item in log_items:
            oh.append((int(item["invocation_start_time_ms"]) - int(item["client_request_time_ms"]))/1000)

        return oh

    def __get_edge_time(self, log_items,src,sink):
        edge_times = []
        for item in log_items:
            edge_times.append(int(item["functions"][sink]["start_delta"] - item["functions"][src]["end_delta"])/1000)
        return edge_times
    '''
    Gives a dictionary of function and edge timings in seconds
    '''
    def __get_timings_dict(self):
        logger.info("Getting timing distribution dictionary")
        logs = self.__get_provenance_logs()
        
        distribution_dict = dict(
            client_overheads=[],
            functions=defaultdict(list),
            edges=defaultdict(list),
            wf_invocation_id = []
        )

        for log in logs:
            wf_invocation_id = log["workflow_invocation_id"]
            distribution_dict["wf_invocation_id"].append(wf_invocation_id)
            distribution_dict["client_overheads"].append((int(log["invocation_start_time_ms"]) - int(log["client_request_time_ms"]))/1000)
            for u in [v for v in self.__xfaas_dag.nodes]:
                exec_time = (log["functions"][u]["end_delta"] - log["functions"][u]["start_delta"])/1000 # seconds
                distribution_dict["functions"][u].append(exec_time)
            for v1,v2 in [e for e in self.__xfaas_dag.edges]:
                edge_key = f"{v1}-{v2}"
                comm_time = (log["functions"][v2]["start_delta"] - log["functions"][v1]["end_delta"])/1000 # seconds
                distribution_dict["edges"][edge_key].append(comm_time)
        
        return distribution_dict

    def __get_timings_dict_with_containers(self,container_ids):
        logger.info("Getting timing distribution dictionary")
        logs = self.__get_provenance_logs()
        
        distribution_dict = dict(
            client_overheads=[],
            functions=defaultdict(list),
            edges=defaultdict(list),
            wf_invocation_id = []
        )

        for log in logs:
            wf_invocation_id = log["workflow_invocation_id"]
            if wf_invocation_id in container_ids:
                distribution_dict["wf_invocation_id"].append(wf_invocation_id)
                distribution_dict["client_overheads"].append((int(log["invocation_start_time_ms"]) - int(log["client_request_time_ms"]))/1000)
                for u in [v for v in self.__xfaas_dag.nodes]:
                    exec_time = (log["functions"][u]["end_delta"] - log["functions"][u]["start_delta"])/1000 # seconds
                    distribution_dict["functions"][u].append(exec_time)
                for v1,v2 in [e for e in self.__xfaas_dag.edges]:
                    edge_key = f"{v1}-{v2}"
                    comm_time = (log["functions"][v2]["start_delta"] - log["functions"][v1]["end_delta"])/1000 # seconds
                    distribution_dict["edges"][edge_key].append(comm_time)
        
        return distribution_dict

    def __get_timings_dict_without_containers(self,container_ids):
        logger.info("Getting timing distribution dictionary")
        logs = self.__get_provenance_logs()
        
        distribution_dict = dict(
            client_overheads=[],
            functions=defaultdict(list),
            edges=defaultdict(list),
            wf_invocation_id = []
        )

        for log in logs:
            wf_invocation_id = log["workflow_invocation_id"]
            if wf_invocation_id not in container_ids:
                distribution_dict["wf_invocation_id"].append(wf_invocation_id)
                distribution_dict["client_overheads"].append((int(log["invocation_start_time_ms"]) - int(log["client_request_time_ms"]))/1000)
                for u in [v for v in self.__xfaas_dag.nodes]:
                    exec_time = (log["functions"][u]["end_delta"] - log["functions"][u]["start_delta"])/1000 # seconds
                    distribution_dict["functions"][u].append(exec_time)
                for v1,v2 in [e for e in self.__xfaas_dag.edges]:
                    edge_key = f"{v1}-{v2}"
                    comm_time = (log["functions"][v2]["start_delta"] - log["functions"][v1]["end_delta"])/1000 # seconds
                    distribution_dict["edges"][edge_key].append(comm_time)
        
        return distribution_dict
    
    def __print_stats_stagewise(self, timings_dict):
        logger.info(":::::: Stagewise Stats Start ::::::")
        func_timings = timings_dict["functions"]
        edge_timings = timings_dict["edges"]
        for f_id in sorted(func_timings):
            logger.info(f"{self.__xfaas_dag.nodes[f_id]['Codename']} \
                        Mean Exec - {statistics.mean(func_timings[f_id])} \
                        Median Exec - {statistics.median(func_timings[f_id])}")
            
        for e_id in sorted(edge_timings):
            split = e_id.split("-")
            u = split[0]
            v = split[1]
            logger.info(f"{self.__xfaas_dag.nodes[u]['Codename']} -> {self.__xfaas_dag.nodes[v]['Codename']} \
                        Mean Exec - {statistics.mean(edge_timings[e_id])} \
                        Median Exec - {statistics.median(edge_timings[e_id])}")

        logger.info(":::::: Stagewise Stats ::::::")

    '''
    Get expected entry count from the dynamism configuration
    '''
    def __get_expected_entry_count(self):
        expected_count = 0
        for conf in self.__exp_conf.values():
            rps = conf["rps"]
            duration = conf["duration"]
            expected_count += rps * duration
        return int(expected_count)
    

    def __add_rps_overlay(self, ax: plt.Axes, len_yticks: int, rps_ticks=None):
        logger.info("Adding overlay for E2E timeline")
        step_x = []
        step_y = []
        conf_items = list(self.__exp_conf.items())
        
        # Calculate step_x and step_y
        max_rps = -1
        time = 0
        step_x.append(time)
        step_y.append(conf_items[0][1]["rps"])
        for key, conf in conf_items:
            time += conf["duration"]
            rps = conf["rps"]
            step_x.append(time)
            step_y.append(rps)

            if rps > max_rps:
                max_rps = rps
        
        ax2 = ax.twinx()
        ax2.set_ylim(ymin=0)
        ax2.set_ylabel("RPS")
        
        if not rps_ticks:
            slots = (max_rps)/(len_yticks-1)
            yticks_ax2 = [round(y,2) for y in np.arange(0, max_rps+slots, slots)]
            ax2.set_yticks(yticks_ax2)
            # NOTE - use the fontdict=fontdict for custom fontsize
            ax2.set_yticklabels([str(y) for y in yticks_ax2]) 
        else:
            ax2.set_yticks(rps_ticks)
            ax2.set_yticklabels([str(y) for y in rps_ticks])

        logger.info(f"Step X - {step_x}:: Step Y - {step_y}")
        ax2.step(step_x, step_y, linestyle='dashed', color='red', linewidth=3)
        return ax


    def __print_cumm_stats(self, cumm_compute_time, cumm_comms_time, cumm_e2e_time):
        logger.info("== Cummulative timings Stats  == ")
        logger.info(f"Mean compute time - {statistics.mean(list(cumm_compute_time))}   Median compute - {statistics.median(list(cumm_compute_time))}")
        logger.info(f"Mean comms time - {statistics.mean(list(cumm_comms_time))}   Median comms time - {statistics.median(list(cumm_comms_time))}")
        logger.info(f"Mean E2E time - {statistics.mean(list(cumm_e2e_time))}   Median E2E time - {statistics.median(list(cumm_e2e_time))}")
        logger.info("== Cummulative timings Statss  == ")

    def __get_cumm_time(self, function_times, edge_times, num_iters):
                           
            source = [n for n, d in self.__xfaas_dag.in_degree() if d == 0][0]
            sink = [n for n, d in self.__xfaas_dag.out_degree() if d == 0][0]
            paths = list(nx.all_simple_paths(self.__xfaas_dag, source, sink))
            
            ## cumm fn exec
            cumm_function_exec = []
            for i in range(num_iters):
                temp = []
                for path in paths:
                    tm = 0
                    for node in path:
                        tm += function_times[node][i]
                    temp.append((tm,path))
                a,b = max(temp)
                cumm_function_exec.append(a)
            

            ## cumm comm time
            cumm_comm_time = []
            for i in range(num_iters):
                temp = []
                for path in paths:
                    tm = 0
                    for j in range(0,len(path)-1):
                        tm += edge_times[f"{path[j]}-{path[j+1]}"][i]
                    temp.append((tm,path))
                a,b = max(temp)
                cumm_comm_time.append(a)
            
            ## e2e
            e2e_time = []
            for i in range(num_iters):
                temp = []
                for path in paths:
                    tm = 0
                    
                    for j in range(0,len(path)-1):
                        tm += edge_times[f"{path[j]}-{path[j+1]}"][i]
                        tm += function_times[path[j]][i]
                    tm += function_times[path[-1]][i]
                    temp.append((tm,path))
                a,b = max(temp)
                e2e_time.append(a)

            # print(cumm_function_exec)
            ss = dict()
            s2 = dict()
            s3 = dict()
            # for p in cumm_function_exec:
            #     xd = str(p[1])
            #     if xd in ss:
            #         ss[xd][0] += 1
            #     else:
            #         ss[xd] = (1,p[0])
                

            # for p in cumm_comm_time:
            #     xd = str(p[1])
            #     if xd in s2:
            #         s2[xd] += 1
            #     else:
            #         s2[xd] = 1
            
            # for p in e2e_time:
            #     xd = str(p[1])
            #     if xd in s3:
            #         s3[xd] += 1
            #     else:
            #         s3[xd] = 1
                
            # print('compute times',ss)
            # print('interfn times',s2)
            # print('e2e times',s3)

            return cumm_function_exec,cumm_comm_time,e2e_time

    def __get__filtered_cumm_time(self, function_times, edge_times, num_iters,wf_invocation_ids,container_invocation_ids,include_continer):
                           
            source = [n for n, d in self.__xfaas_dag.in_degree() if d == 0][0]
            sink = [n for n, d in self.__xfaas_dag.out_degree() if d == 0][0]
            paths = list(nx.all_simple_paths(self.__xfaas_dag, source, sink))
            
            if include_continer == True:
            ## cumm fn exec
                cumm_function_exec = []
                for i in range(num_iters):
                    temp = []
                    for path in paths:
                        tm = 0
                        for node in path:
                            tm += function_times[node][i]
                        temp.append(tm)
                    if wf_invocation_ids[i] in container_invocation_ids:
                        cumm_function_exec.append(max(temp))
                

                ## cumm comm time
                cumm_comm_time = []
                for i in range(num_iters):
                    temp = []
                    for path in paths:
                        tm = 0
                        for j in range(0,len(path)-1):
                            tm += edge_times[f"{path[j]}-{path[j+1]}"][i]
                        temp.append(tm)
                    if wf_invocation_ids[i] in container_invocation_ids:
                        cumm_comm_time.append(max(temp))
                
                ## e2e
                e2e_time = []
                for i in range(num_iters):
                    temp = []
                    for path in paths:
                        tm = 0
                        
                        for j in range(0,len(path)-1):
                            tm += edge_times[f"{path[j]}-{path[j+1]}"][i]
                            tm += function_times[path[j]][i]
                        tm += function_times[path[-1]][i]
                        temp.append(tm)
                    if wf_invocation_ids[i] in container_invocation_ids:
                        e2e_time.append(max(temp))
            else:
                ## cumm fn exec
                cumm_function_exec = []
                for i in range(num_iters):
                    temp = []
                    for path in paths:
                        tm = 0
                        for node in path:
                            tm += function_times[node][i]
                        temp.append(tm)
                    if wf_invocation_ids[i] not in container_invocation_ids:
                        cumm_function_exec.append(max(temp))
                

                ## cumm comm time
                cumm_comm_time = []
                for i in range(num_iters):
                    temp = []
                    for path in paths:
                        tm = 0
                        for j in range(0,len(path)-1):
                            tm += edge_times[f"{path[j]}-{path[j+1]}"][i]
                        temp.append(tm)
                    if wf_invocation_ids[i] not in container_invocation_ids:
                        cumm_comm_time.append(max(temp))
                
                ## e2e
                e2e_time = []
                for i in range(num_iters):
                    temp = []
                    for path in paths:
                        tm = 0
                        
                        for j in range(0,len(path)-1):
                            tm += edge_times[f"{path[j]}-{path[j+1]}"][i]
                            tm += function_times[path[j]][i]
                        tm += function_times[path[-1]][i]
                        temp.append(tm)
                    if wf_invocation_ids[i] not in container_invocation_ids:
                        e2e_time.append(max(temp))



            return cumm_function_exec,cumm_comm_time,e2e_time



    def __get_azure_containers(self, log_items: list):
        # array for storing the workflow invocation ids
        wf_invocation_ids = set() # TODO - check with VK.
        god_dict = {}
        ans = []
        mins = []
        sorted_dynamo_items = log_items
        min_start_time  = sorted_dynamo_items[0]["invocation_start_time_ms"]
        # print(sorted_dynamo_items)
        function_map = set()
        for item in sorted_dynamo_items:
            functions = item['functions']
            workflow_start_time = item['invocation_start_time_ms']

            # New addition - 
            wf_invocation_id = item['workflow_invocation_id']

            for function in functions:
                if "cid"  in functions[function]:
                    cid = functions[function]['cid']
                    function_start_delta = functions[function]['start_delta']
                    function_start_time = int(workflow_start_time) + function_start_delta
                    if cid == '':
                        continue
                    if cid not in god_dict:
                        god_dict[cid] = []
                        
                        god_dict[cid].append((function_start_time,int(workflow_start_time), wf_invocation_id,function))
                    else:
                        god_dict[cid].append((function_start_time,int(workflow_start_time), wf_invocation_id,function))  
                    
                           

        
        functions = []
        print("God dict length: ", len(god_dict.keys()))
        for cid in god_dict:
            god_dict[cid].sort()
            ans.append(god_dict[cid][0])
            # mins.append((god_dict[cid][0][0]-int(min_start_time))/1000)
            mins.append((god_dict[cid][0][1]-int(min_start_time))/1000)
            wf_invocation_ids.add(god_dict[cid][0][2])
            functions.append(god_dict[cid][0][3])
        
        return sorted(mins), wf_invocation_ids
    
    # TODO - populate the aws container traces function 
    def __get_aws_containers():
        pass

    '''
    Plot e2e timeline plot with and without overlay of rps
    NOTE - the e2e timeline will be with respect to the invocation start time and not the client_request
    '''
    def plot_e2e_timeline(self, xticks: list, yticks: list, is_overlay: bool,region):
        logger.info(f"Plotting E2E timeline with rps_overlay={is_overlay}")
        logs = self.__get_provenance_logs()
        timestamps = [int(item["invocation_start_time_ms"]) for item in sorted(logs, key=lambda k: int(k["invocation_start_time_ms"]))] # NOTE - the timeline is w.r.t client
        timeline = [(t-timestamps[0])/1000 for t in timestamps] # timeline in seconds
        e2e_time = self.__get_e2e_time(log_items=sorted(logs, key=lambda k: int(k["invocation_start_time_ms"])))
        oh = self.__get_overheads(log_items=sorted(logs, key=lambda k: int(k["invocation_start_time_ms"])))
        
        logger.info(f"Entry Count in Timeline - {len(timeline)}, Expected Entry Count - {self.__get_expected_entry_count()}")
        # self.__get_azure_containers(log_items=sorted(logs, key=lambda k: int(k["invocation_start_time_ms"])))
        # fontdict = {'size': 12} # NOTE - custom fontdict 
        fig, ax = plt.subplots()
        fig.set_dpi(400)
        ax.yaxis.set_minor_locator(tck.AutoMinorLocator())
        
        '''
        NOTE - uncomment to set custom tick parameters and tick label fontsize
        '''
        # ax.xaxis.set_tick_params(which='major', labelsize=fontdict['size'])
        # ax.yaxis.set_tick_params(which='major', labelsize=fontdict['size'])
        
        # NOTE - pass the fontdict parameter here (...,fontdict=fontdict)
        ax.set_ylabel("E2E Time (sec)") 
        ax.set_xlabel("Timeline (sec)")
        '''
        Setting xtcks and yticks parameters here
        '''
        if not yticks == []:
            ax.set_yticks(yticks)
            ax.set_yticklabels([str(y) for y in yticks])

        if not xticks == []:
            ax.set_xticks(xticks)
            ax.set_xticklabels(str(x) for x in xticks)
        
       
        ax.plot(timeline, e2e_time)
        print(e2e_time[0:23])
        

        if is_overlay:
            yticks_mod = [y for y in ax.get_yticks() if y >= 0]
            ax = self.__add_rps_overlay(ax=ax, len_yticks=len(yticks_mod))        

        '''
        Setting grid parameters here
        '''
        ax.set_ylim(ymin=0, ymax=max(ax.get_yticks()))
        # ax.set_xlim(xmin=0, xmax=max(ax.get_xticks()))

        # NOTE - plotting the container spawn times here
        if self.__exp_desc.get("csp") == "azure" or self.__exp_desc.get("csp") == "azure_v2":
            container_spawn_times, _ = self.__get_azure_containers(log_items=sorted(logs, key=lambda k: int(k["invocation_start_time_ms"])))

            ax.plot(container_spawn_times, [ax.get_ylim()[1]/2 for i in range(0, len(container_spawn_times))], color='green', marker='o', markersize=8, linestyle='None')
            ax.vlines(x=container_spawn_times, ymin=0, ymax=ax.get_ylim()[1]/2, linestyles='dashed', color='darkgrey', linewidth=2)

        if self.__exp_desc.get("csp") == "aws":
            logger.info("TODO: Complete the aws container traces function")
            # log_items=sorted(logs, key=lambda k: int(k["invocation_start_time_ms"]))
            # min_timestamp = int(log_items[0]["invocation_start_time_ms"])
            # aws_containers_ts = aws_containers.get_container_count(self.__app_name)
            # aws_containers_ts = dict(sorted(aws_containers_ts.items()))
            # container_spawn_times = list(aws_containers_ts.keys()) 
            # import datetime
            # wall_clock_times = [datetime.datetime.fromtimestamp(int(t)).strftime('%Y-%m-%d %H:%M:%S') for t in container_spawn_times]
            # print('wall clock: ',wall_clock_times)
            
            # container_spawn_times = [(int(t) - min_timestamp/1000) for t in container_spawn_times]
            # print('from portal: ',container_spawn_times)
            # ## epoch time to actual time
            
            # ax.plot(container_spawn_times, [ax.get_ylim()[1]/2 for i in range(0, len(container_spawn_times))], color='green', marker='o', markersize=8, linestyle='None')
            # ax.vlines(x=container_spawn_times, ymin=0, ymax=ax.get_ylim()[1]/2, linestyles='dashed', color='darkgrey', linewidth=2)
            # print('Timeline: ',aws_containers_ts)
           

        

        ax.grid(axis="y", which="major", linestyle="-", color="black")
        ax.grid(axis="y", which="minor", linestyle="-", color="darkgrey")
        ax.set_axisbelow(True)
        
        if is_overlay:
            fig.savefig(self.__plots_dir / \
                        f"e2e_timeline_with_overlay_{self.__get_outfile_prefix()}.{self.__format}", bbox_inches='tight')
        else:
            fig.savefig(self.__plots_dir / \
                        f"e2e_timeline_{self.__get_outfile_prefix()}.{self.__format}", bbox_inches='tight')


    '''
    Plot Stagewise
    '''
    def plot_stagewise(self, yticks: list, figwidth=None):
        logger.info("Plotting Stagewise Boxplots")
        distribution_dict = self.__get_timings_dict()

        fig, ax = plt.subplots()
        fig.set_dpi(450)

        if figwidth:
            fig.set_figwidth(figwidth)

        ax.set_ylabel("Time (sec)") # NOTE - use ...,fontdict=fontdict for custom font
        ax.yaxis.set_minor_locator(tck.AutoMinorLocator())

        if not yticks == []:
            ax.set_yticks(yticks)
            ax.set_yticklabels([str(y) for y in yticks])
        
        # NOTE for custom tick params uncomment this
        # ax.yaxis.set_tick_params(which='major', labelsize=fontdict['size']) 
        # ax.xaxis.set_tick_params(which='major', labelsize=fontdict['size'])

        # TextProcess yticks - 

        interleaved_label_ids = []
        interleaved_data = []
        visited = set()
        def get_edges(n):
            return [(u,v) for u,v in self.__xfaas_dag.edges if u == n]
        
        def get_color(id):
            if "-" in id:
                return "lightgreen"
            else:
                return "lightblue"
        
        def get_label_color(id):
            if "-" in id:
                return "green"
            else:
                return "blue"     
            
        def get_data(id):
            if "-" in id:
                return np.array(distribution_dict["edges"][id])
            else:
                return np.array(distribution_dict["functions"][id])
            
        def get_labels(label_ids):
            labels = []
            for label in label_ids:
                if "-" in label:
                    split = label.split("-")
                    node1 = split[0]
                    node2 = split[1]
                    labels.append(f"{self.__xfaas_dag.nodes[node1]['Codename']}-{self.__xfaas_dag.nodes[node2]['Codename']}")
                else:
                    labels.append(self.__xfaas_dag.nodes[label]['Codename'])
            return labels


        # create some sort of an ordered labels for the interleaved plot
        for u in self.__xfaas_dag.nodes:
            if u not in visited:
                interleaved_label_ids.append(u)
                edges = get_edges(u)
                interleaved_label_ids += [f"{n1}-{n2}" for n1, n2 in edges]
                visited.add(u)

        interleaved_data = [np.array(distribution_dict["client_overheads"])] + [get_data(id) for id in interleaved_label_ids]    
        # rectangular box plot
        bplot1 = ax.boxplot(interleaved_data,
                            vert=True,  # vertical box alignment
                            patch_artist=True,
                            widths=0.2,
                            showfliers=False)  # fill with color
                            # labels=interfunction_labels)
        
        interleaved_labels_modified = ["INIT-OH"] + get_labels(interleaved_label_ids)
        logger.info(f"Interleaved Labels - {interleaved_labels_modified}")
        
        ax.set_xticklabels(interleaved_labels_modified, 
                           rotation=90)
        ax.set_ylim(ymin=0, ymax=max(ax.get_yticks()))

        interleaved_label_ids = ['init-oh'] + interleaved_label_ids

        for idx, patch in enumerate(bplot1['boxes']):
            # NOTE - set facecolor for the client overheads
            if idx == 0:
                patch.set_facecolor('red')
            else:
                patch.set_facecolor(get_color(interleaved_label_ids[idx]))
        # set the label colors
        for idx, xtick in enumerate(ax.get_xticklabels()[0:len(interleaved_label_ids)]):
            if idx == 0:
                xtick.set_color('red')
            else:
                xtick.set_color(get_label_color(interleaved_label_ids[idx]))

        ##### VLINES #####        
        # add lighter vlines between the boxes themselves
        _xloc = ax.get_xticks()[0: len(interleaved_label_ids)]
        vlines_x_between = []
        for idx in range(0, len(_xloc)-1):
            vlines_x_between.append(_xloc[idx]/2 + _xloc[idx+1]/2)
        ax.vlines(x=vlines_x_between, ymin=0, ymax=ax.get_ylim()[1], linestyles='solid', color='darkgrey', linewidth=1.5)
        ###### VLINES ####

        ax.grid(axis="y", which="major", linestyle="-", color="black")
        ax.grid(axis="y", which="minor", linestyle="-", color="grey")
        ax.set_axisbelow(True)

        self.__print_stats_stagewise(distribution_dict)
        
        fig.savefig(self.__plots_dir / f"stagewise_{self.__get_outfile_prefix()}.{self.__format}", bbox_inches='tight')
        

    '''
    Plot cummulative e2e plots
    '''
    def plot_cumm_e2e(self, yticks: list):
        fig, ax = plt.subplots()
        fig.set_dpi(400)
        # fig.set_figwidth(9)
        ax.set_ylabel("Time (sec)")
        cumm_labels = [r'$\sum Exec$', r'$\sum Comms$', r'$\sum E2E$']

        # NOTE - for custom size uncomment these with fontdict
        fontdict = {'size': 20} 
        ax.yaxis.set_tick_params(which='major', labelsize=fontdict['size'])
        
        distribution_dict = self.__get_timings_dict()
        # cumm_func_time = get_cumm_time_func(time_map=distribution_dict["functions"], num_iters=len(e2e_all_sessions))
        cumm_compute_time, cumm_comms_time, cumm_e2e_time = self.__get_cumm_time(distribution_dict["functions"],
                                                                                distribution_dict["edges"],
                                                                                num_iters=len(self.__get_provenance_logs()))

        print(cumm_compute_time[0:20])
        print(cumm_comms_time[0:20])
        print(cumm_e2e_time[0:20])

        cumm_compute_time = cumm_compute_time[0:23]
        cumm_comms_time = cumm_comms_time[0:23]
        cumm_e2e_time = cumm_e2e_time[0:23]

        bplot2 = ax.boxplot([np.array(cumm_compute_time), np.array(cumm_comms_time), np.array(cumm_e2e_time)],
                             vert=True,
                             widths=0.2,
                             patch_artist=True,
                             showfliers=False)
        
        if not yticks == []:
            ax.set_yticks(yticks)
            ax.set_yticklabels([str(x) for x in yticks])
        
        ax.set_xticks([x+1 for x in range(0, len(cumm_labels))])
        ax.set_xticklabels(cumm_labels)

        # Set ylim
        ax.set_ylim(ymin=0, ymax=max(ax.get_yticks()))
        # color='pink'
        colors = ['blue', 'green', 'brown']
        for patch, color in zip(bplot2['boxes'], colors):
            patch.set_facecolor(color)

        _xloc = ax.get_xticks()
        vlines_x_between = []
        for idx in range(0, len(_xloc)-1):
            vlines_x_between.append(_xloc[idx]/2 + _xloc[idx+1]/2)
        ax.vlines(x=vlines_x_between, ymin=0, ymax=ax.get_ylim()[1], linestyles='solid', color='darkgrey', linewidth=1.5)

        ax.yaxis.set_minor_locator(tck.AutoMinorLocator())
        ax.grid(axis="y", which="major", linestyle="-", color="black")
        ax.grid(axis="y", which="minor", linestyle="-", color="grey")
        ax.set_axisbelow(True)


        self.__print_cumm_stats(cumm_compute_time=cumm_compute_time,
                                cumm_comms_time=cumm_comms_time,
                                cumm_e2e_time=cumm_e2e_time)
        
        fig.savefig(self.__plots_dir / f"cumm_{self.__get_outfile_prefix()}_{self.__exp_desc.get('rps')}.{self.__format}", bbox_inches='tight')

    '''
    Box plot containng the e2e times for invocations which start the containers
    vs the e2e times for invocations that do not start the container
    '''
    def plot_e2e_invocations_wnwo_containers(self, csp: str, yticks: list):
        logger.info(f"Plotting e2e boxplots for invocations wnwo containers")
        logs = self.__get_provenance_logs()
        
        if csp == 'azure':
            # NOTE - this returns a "set" of ids
            _ , container_wf_invocations_ids = self.__get_azure_containers(log_items=sorted(logs, key=lambda k: int(k["invocation_start_time_ms"])))
        if csp == 'aws':
            #TODO - structure aws container fetching similar to azure
            # _, container_wf_invocation_ids = self.__get_aws_containers()
            pass

        # logger.info(f"Invocation Ids with conatiner spawn :: CSP {csp} - {container_wf_invocations_ids}")
        
        sink_node = [node for node in self.__xfaas_dag.nodes if self.__xfaas_dag.out_degree(node) == 0][0]
        
        e2e_wo_containers = []
        e2e_w_containers = []
        
        # Formed data for plots
        for log in logs:
            if log["workflow_invocation_id"] in container_wf_invocations_ids:
                e2e_w_containers.append(int(log["functions"][sink_node]["end_delta"])/1000)
            else:
                e2e_wo_containers.append(int(log["functions"][sink_node]["end_delta"])/1000)

        print(len(e2e_w_containers))
        print(len(e2e_wo_containers))
        print(len(logs))
        fig, ax = plt.subplots()
        fig.set_dpi(400)
        ax.set_ylabel("Time (sec)")
        labels = ['E2E w/o\nContainer Spawn', 'E2E w\nContainer Spawn']

        bplot2 = ax.boxplot([np.array(e2e_wo_containers), np.array(e2e_w_containers)],
                             vert=True,
                             widths=0.1,
                             patch_artist=True,
                             showfliers=False)
        
        if not yticks == []:
            ax.set_yticks(yticks)
            ax.set_yticklabels([str(x) for x in yticks])
        
        ax.set_xticks([x+1 for x in range(0, len(labels))])
        ax.set_xticklabels(labels)

        # Set ylim
        ax.set_ylim(ymin=0, ymax=max(ax.get_yticks()))
        # color='pink'
        colors = ['lightblue', 'blue']
        for patch, color in zip(bplot2['boxes'], colors):
            patch.set_facecolor(color)

        _xloc = ax.get_xticks()
        vlines_x_between = []
        for idx in range(0, len(_xloc)-1):
            vlines_x_between.append(_xloc[idx]/2 + _xloc[idx+1]/2)
        ax.vlines(x=vlines_x_between, ymin=0, ymax=ax.get_ylim()[1], linestyles='solid', color='darkgrey', linewidth=1.5)

        ax.yaxis.set_minor_locator(tck.AutoMinorLocator())
        ax.grid(axis="y", which="major", linestyle="-", color="black")
        ax.grid(axis="y", which="minor", linestyle="-", color="grey")
        ax.set_axisbelow(True)
        # 

        fig.savefig(self.__plots_dir / f"e2e_wnwo_container_contrast_{self.__get_outfile_prefix()}.{self.__format}", bbox_inches='tight')
        return e2e_w_containers, e2e_wo_containers

    
    '''
    Plot cummulative e2e plots for with and wo continaers
    '''
    def plot_cumm_e2e_container(self, csp,yticks: list):
        logs = self.__get_provenance_logs()
        distribution_dict = self.__get_timings_dict()
        if csp == 'azure':
            # NOTE - this returns a "set" of ids
            _ , container_wf_invocations_ids = self.__get_azure_containers(log_items=sorted(logs, key=lambda k: int(k["invocation_start_time_ms"])))
        if csp == 'aws':
            #TODO - structure aws container fetching similar to azure
            # _, container_wf_invocation_ids = self.__get_aws_containers()
            pass
        logger.info(f"Invocation Ids with conatiner spawn :: CSP {csp} - {container_wf_invocations_ids}")
        
        sink_node = [node for node in self.__xfaas_dag.nodes if self.__xfaas_dag.out_degree(node) == 0][0]
        cumm_compute_time_wo, cumm_comms_time_wo, cumm_e2e_time_wo = self.__get__filtered_cumm_time(distribution_dict["functions"],
                                                                                distribution_dict["edges"],
                                                                                num_iters=len(self.__get_provenance_logs()),
                                                                                wf_invocation_ids= distribution_dict["wf_invocation_id"],
                                                                                container_invocation_ids= container_wf_invocations_ids,
                                                                                include_continer=False)
        cumm_compute_time_w, cumm_comms_time_w, cumm_e2e_time_w = self.__get__filtered_cumm_time(distribution_dict["functions"],
                                                                                distribution_dict["edges"],
                                                                                num_iters=len(self.__get_provenance_logs()),
                                                                                wf_invocation_ids= distribution_dict["wf_invocation_id"],
                                                                                container_invocation_ids= container_wf_invocations_ids,
                                                                                include_continer=True)

        return cumm_compute_time_w,cumm_compute_time_wo,cumm_comms_time_w,cumm_comms_time_wo,cumm_e2e_time_w,cumm_e2e_time_wo
    '''
    Plot Stagewise
    '''
    def plot_stagewise_containers(self,csp, yticks: list, figwidth=None):
        logs = self.__get_provenance_logs()
        if csp == 'azure':
        # NOTE - this returns a "set" of ids
            _ , container_wf_invocations_ids = self.__get_azure_containers(log_items=sorted(logs, key=lambda k: int(k["invocation_start_time_ms"])))
        if csp == 'aws':
            #TODO - structure aws container fetching similar to azure
            # _, container_wf_invocation_ids = self.__get_aws_containers()
            pass
        logger.info("Plotting Stagewise Boxplots")
        distribution_dict = self.__get_timings_dict_with_containers(container_wf_invocations_ids)

        # fig, ax = plt.subplots()
        # fig.set_dpi(450)

        # if figwidth:
        #     fig.set_figwidth(figwidth)

        # ax.set_ylabel("Time (sec)") # NOTE - use ...,fontdict=fontdict for custom font
        # ax.yaxis.set_minor_locator(tck.AutoMinorLocator())

        # if not yticks == []:
        #     ax.set_yticks(yticks)
        #     ax.set_yticklabels([str(y) for y in yticks])
        
        # NOTE for custom tick params uncomment this
        # ax.yaxis.set_tick_params(which='major', labelsize=fontdict['size']) 
        # ax.xaxis.set_tick_params(which='major', labelsize=fontdict['size'])

        # TextProcess yticks - 

        interleaved_label_ids = []
        interleaved_data = []
        visited = set()
        def get_edges(n):
            return [(u,v) for u,v in self.__xfaas_dag.edges if u == n]
        
        def get_color(id):
            if "-" in id:
                return "lightgreen"
            else:
                return "lightblue"
        
        def get_label_color(id):
            if "-" in id:
                return "green"
            else:
                return "blue"     
            
        def get_data(id):
            if "-" in id:
                return np.array(distribution_dict["edges"][id])
            else:
                return np.array(distribution_dict["functions"][id])
            
        def get_labels(label_ids):
            labels = []
            for label in label_ids:
                if "-" in label:
                    split = label.split("-")
                    node1 = split[0]
                    node2 = split[1]
                    labels.append(f"{self.__xfaas_dag.nodes[node1]['Codename']}-{self.__xfaas_dag.nodes[node2]['Codename']}")
                else:
                    labels.append(self.__xfaas_dag.nodes[label]['Codename'])
            return labels


        # create some sort of an ordered labels for the interleaved plot
        for u in self.__xfaas_dag.nodes:
            if u not in visited:
                interleaved_label_ids.append(u)
                edges = get_edges(u)
                interleaved_label_ids += [f"{n1}-{n2}" for n1, n2 in edges]
                visited.add(u)

        interleaved_data = [np.array(distribution_dict["client_overheads"])] + [get_data(id) for id in interleaved_label_ids]    
        interleaved_label_ids_new = []
        for i in interleaved_label_ids:
            if '-' not in i:
                interleaved_label_ids_new.append(i)

        intereleaved_functions_with_cont = [get_data(id) for id in interleaved_label_ids_new]
        intereleaved_functions_with_cont = (intereleaved_functions_with_cont, interleaved_label_ids_new)
        
        # rectangular box plot
        # bplot1 = ax.boxplot(interleaved_data,
        #                     vert=True,  # vertical box alignment
        #                     patch_artist=True,
        #                     widths=0.2,
        #                     showfliers=False)  # fill with color
        #                     # labels=interfunction_labels)
        
        # interleaved_labels_modified = ["INIT-OH"] + get_labels(interleaved_label_ids)
        # logger.info(f"Interleaved Labels - {interleaved_labels_modified}")
        
        # ax.set_xticklabels(interleaved_labels_modified, 
        #                    rotation=90)
        # ax.set_ylim(ymin=0, ymax=max(ax.get_yticks()))

        # interleaved_label_ids = ['init-oh'] + interleaved_label_ids

        # for idx, patch in enumerate(bplot1['boxes']):
        #     # NOTE - set facecolor for the client overheads
        #     if idx == 0:
        #         patch.set_facecolor('red')
        #     else:
        #         patch.set_facecolor(get_color(interleaved_label_ids[idx]))

        # # set the label colors
        # for idx, xtick in enumerate(ax.get_xticklabels()[0:len(interleaved_label_ids)]):
        #     if idx == 0:
        #         xtick.set_color('red')
        #     else:
        #         xtick.set_color(get_label_color(interleaved_label_ids[idx]))

        # ##### VLINES #####        
        # # add lighter vlines between the boxes themselves
        # _xloc = ax.get_xticks()[0: len(interleaved_label_ids)]
        # vlines_x_between = []
        # for idx in range(0, len(_xloc)-1):
        #     vlines_x_between.append(_xloc[idx]/2 + _xloc[idx+1]/2)
        # ax.vlines(x=vlines_x_between, ymin=0, ymax=ax.get_ylim()[1], linestyles='solid', color='darkgrey', linewidth=1.5)
        # ###### VLINES ####

        # ax.grid(axis="y", which="major", linestyle="-", color="black")
        # ax.grid(axis="y", which="minor", linestyle="-", color="grey")
        # ax.set_axisbelow(True)

        # self.__print_stats_stagewise(distribution_dict)
        
        # fig.savefig(self.__plots_dir / f"stagewise_w_containers_{self.__get_outfile_prefix()}.{self.__format}", bbox_inches='tight')






        logger.info("Plotting Stagewise Boxplots")
        distribution_dict = self.__get_timings_dict_without_containers(container_wf_invocations_ids)

        # fig, ax = plt.subplots()
        # fig.set_dpi(450)

        # if figwidth:
        #     fig.set_figwidth(figwidth)

        # ax.set_ylabel("Time (sec)") # NOTE - use ...,fontdict=fontdict for custom font
        # ax.yaxis.set_minor_locator(tck.AutoMinorLocator())

        # if not yticks == []:
        #     ax.set_yticks(yticks)
        #     ax.set_yticklabels([str(y) for y in yticks])
        
        # NOTE for custom tick params uncomment this
        # ax.yaxis.set_tick_params(which='major', labelsize=fontdict['size']) 
        # ax.xaxis.set_tick_params(which='major', labelsize=fontdict['size'])

        # TextProcess yticks - 

        interleaved_label_ids = []
        interleaved_data = []
        visited = set()
        def get_edges(n):
            return [(u,v) for u,v in self.__xfaas_dag.edges if u == n]
        
        def get_color(id):
            if "-" in id:
                return "lightgreen"
            else:
                return "lightblue"
        
        def get_label_color(id):
            if "-" in id:
                return "green"
            else:
                return "blue"     
            
        def get_data(id):
            if "-" in id:
                return np.array(distribution_dict["edges"][id])
            else:
                return np.array(distribution_dict["functions"][id])
            
        def get_labels(label_ids):
            labels = []
            for label in label_ids:
                if "-" in label:
                    split = label.split("-")
                    node1 = split[0]
                    node2 = split[1]
                    labels.append(f"{self.__xfaas_dag.nodes[node1]['Codename']}-{self.__xfaas_dag.nodes[node2]['Codename']}")
                else:
                    labels.append(self.__xfaas_dag.nodes[label]['Codename'])
            return labels


        # create some sort of an ordered labels for the interleaved plot
        for u in self.__xfaas_dag.nodes:
            if u not in visited:
                interleaved_label_ids.append(u)
                edges = get_edges(u)
                interleaved_label_ids += [f"{n1}-{n2}" for n1, n2 in edges]
                visited.add(u)

        interleaved_data = [np.array(distribution_dict["client_overheads"])] + [get_data(id) for id in interleaved_label_ids]    
        interleaved_label_ids_new = []

        for i in interleaved_label_ids:
            if '-' not in i:
                interleaved_label_ids_new.append(i)
        # print(interleaved_label_ids_new)

        intereleaved_functions_without_cont = [get_data(id) for id in interleaved_label_ids_new]
        intereleaved_functions_without_cont = (intereleaved_functions_without_cont,interleaved_label_ids_new)
        return intereleaved_functions_with_cont,intereleaved_functions_without_cont
        # rectangular box plot
        # bplot1 = ax.boxplot(interleaved_data,
        #                     vert=True,  # vertical box alignment
        #                     patch_artist=True,
        #                     widths=0.2,
        #                     showfliers=False)  # fill with color
        #                     # labels=interfunction_labels)
        
        # interleaved_labels_modified = ["INIT-OH"] + get_labels(interleaved_label_ids)
        # logger.info(f"Interleaved Labels - {interleaved_labels_modified}")
        
        # ax.set_xticklabels(interleaved_labels_modified, 
        #                    rotation=90)
        # ax.set_ylim(ymin=0, ymax=max(ax.get_yticks()))

        # interleaved_label_ids = ['init-oh'] + interleaved_label_ids

        # for idx, patch in enumerate(bplot1['boxes']):
        #     # NOTE - set facecolor for the client overheads
        #     if idx == 0:
        #         patch.set_facecolor('red')
        #     else:
        #         patch.set_facecolor(get_color(interleaved_label_ids[idx]))

        # # set the label colors
        # for idx, xtick in enumerate(ax.get_xticklabels()[0:len(interleaved_label_ids)]):
        #     if idx == 0:
        #         xtick.set_color('red')
        #     else:
        #         xtick.set_color(get_label_color(interleaved_label_ids[idx]))

        # ##### VLINES #####        
        # # add lighter vlines between the boxes themselves
        # _xloc = ax.get_xticks()[0: len(interleaved_label_ids)]
        # vlines_x_between = []
        # for idx in range(0, len(_xloc)-1):
        #     vlines_x_between.append(_xloc[idx]/2 + _xloc[idx+1]/2)
        # ax.vlines(x=vlines_x_between, ymin=0, ymax=ax.get_ylim()[1], linestyles='solid', color='darkgrey', linewidth=1.5)
        # ###### VLINES ####

        # ax.grid(axis="y", which="major", linestyle="-", color="black")
        # ax.grid(axis="y", which="minor", linestyle="-", color="grey")
        # ax.set_axisbelow(True)

        # self.__print_stats_stagewise(distribution_dict)
        
        # fig.savefig(self.__plots_dir / f"stagewise_wo_containers_{self.__get_outfile_prefix()}.{self.__format}", bbox_inches='tight')