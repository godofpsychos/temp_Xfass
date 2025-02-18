# Python base imports
import os
import sys
import pathlib
import shutil
import traceback
from jinja2 import Environment, FileSystemLoader
import json
import copy
import logging
# Serwo imports
import python.src.utils.generators.aws.sfn_yaml_generator as AWSSfnYamlGenerator
import python.src.utils.generators.aws.sfn_asl_generator as AWSSfnAslBuilder
from python.src.utils.classes.aws.user_dag import UserDag as AWSUserDag
from python.src.utils.classes.aws.trigger_types import TriggerType
from python.src.utils.classes.commons.logger import LoggerFactory
import random
logger = LoggerFactory.get_logger(__file__, log_level="INFO")


class AWS:
    # filenames
    # FIXME - change the filenames consistently for different clouds
    __yaml_file = "template.yaml"
    __json_file = "statemachine.asl.json"

    """
    Constructor
    """

    def __init__(self, user_dir, dag_desc_filename, trigger_type, part_id, region):
        # populating these from external modules
        # TODO - parameterize the region as well (hardcoded for now)
        self.__region = region
        self.__user_dir = pathlib.Path(user_dir)
        self.__dag_definition_file = dag_desc_filename
        self.__trigger_type = TriggerType.get_trigger_type(trigger_type)
        self.__part_id = part_id

        # file parent directory
        """
        TODO - change this parent directory accordingly if we plan to move
        this file into another folder
        """
        self.__parent_directory_path = pathlib.Path(__file__).parent

        # xfaas specfic directories
        self.__serwo_build_dir = self.__user_dir / f"build/workflow"
        self.__serwo_resources_dir = self.__serwo_build_dir / f"resources"
        self.__serwo_utils_dir = self.__parent_directory_path / f"python"
        self.__runner_template_dir = (
            self.__parent_directory_path / f"python/src/runner-templates/aws"
        )
        self.__yaml_template_dir = (
            self.__parent_directory_path
            / f"python/src/faas-templates/aws/yaml-templates"
        )
        self.__dag_definition_path = self.__user_dir / self.__dag_definition_file

        # aws specfic directories
        self.__aws_build_dir = self.__serwo_build_dir / f"aws"
        self.__serwo_functions_build_dir = self.__aws_build_dir / f"functions"
        self.__sam_build_dir = self.__aws_build_dir / f"sam-build"

        # DAG related parameters
        self.__user_dag = AWSUserDag(self.__dag_definition_path)
        self.__sam_stackname = (
            ##random 3 digit number

            "XFaaSApp-" + self.__user_dag.get_user_dag_name() + str(random.randint(100, 999))
        )  # TODO - add nonce here

        # TODO - convert this aws-clouformation-outputs -> self.__getname() + self.__region + self.__part_id
        self.__outputs_filepath = (
            self.__serwo_resources_dir / f"aws-{self.__region}-{self.__part_id}.json"
        )

    """
    NOTE - This is a replacement for the create_env.sh file
    Creates an environment within the build directory which stores all the files and 
    deployment metadata within the build directory

    TODO - delete the file under scripts/aws/create_env.sh
    TODO - remove the "functions" hardcoded directory name and maybe 
           read it from a config?
    """

    def __create_environment(self):
        # Create functions directory
        function_path = self.__aws_build_dir / f"functions"
        if not os.path.exists(self.__aws_build_dir):
            os.makedirs(self.__aws_build_dir)

        if not os.path.exists(function_path):
            os.makedirs(function_path)

        # add the init.py file for each of the created directories
        pathlib.Path(function_path / "__init__.py").touch()
        pathlib.Path(self.__aws_build_dir / "__init__.py").touch()

        return function_path

    """
    NOTE - This is a replacement for the create_lambda_fn.sh file
    Places / Creates appropriate files in the user directories to initate
    the build process for AWS
    
    TODO - delete the file under scripts/aws/create_lambda_fn.sh
    TODO - dont' fixate on the name, requirements.txt

    """

    def __create_lambda_fns(
        self,
        user_fn_path,
        serwo_fn_build_dir,
        fn_name,
        fn_module_name,
        runner_template_filename,
        runner_template_dir,
        runner_filename,
    ):
        # TODO - should this be taken in from the dag-description?
        fn_requirements_filename = "requirements.txt"
        fn_dir = serwo_fn_build_dir / f"{fn_name}"

        logger.info(f"Creating function directory for {fn_name}")
        if not os.path.exists(fn_dir):
            os.makedirs(fn_dir)
        pathlib.Path(fn_dir / "__init__.py").touch()

        """
        place the requirements.txt for the 
        user function in serwo function directory
        """
        logger.info(f"Moving requirements file for {fn_name} for user at to {fn_dir}")
        shutil.copyfile(src=f"{user_fn_path / fn_requirements_filename}", dst=f"{fn_dir / fn_requirements_filename}")

        # Add the XFaaS specific requrirements on to the function requirements
        logger.info(
            f"Adding default requirements {fn_name}"
        )
        requriements_path = fn_dir / fn_requirements_filename
        self.__append_xfaas_default_requirements(requriements_path)


        """
        place the dependencies folder in the user function path
        """
        if os.path.exists(user_fn_path / "dependencies"):
            shutil.copytree(
                user_fn_path / "dependencies", 
                fn_dir / "dependencies", 
                dirs_exist_ok=True
            )

        """
        place all xfaas code in user fn dir
        """
        logger.info(f"Moving xfaas boilerplate for {fn_name}")

        shutil.copytree(src=self.__serwo_utils_dir, dst=f'{fn_dir / "python"}', dirs_exist_ok=True)

        """g
        generate runners
        """
        logger.info(f"Generating Runners for function {fn_name}")

        fnr_string = f"USER_FUNCTION_PLACEHOLDER"
        temp_runner_path = user_fn_path / f"{fn_name}_temp_runner.py"
        runner_template_path = runner_template_dir / runner_template_filename
        
        print("Here", runner_template_path)
        with open(runner_template_path, "r") as file:
            contents = file.read()
            contents = contents.replace(fnr_string, fn_module_name)

        with open(temp_runner_path, "w") as file:
            file.write(contents)

        # TODO - Fix the stickytape issue for AWS
        # GitHub Issue link - https://github.com/dream-lab/XFaaS/issues/4
        """
        Sticytape the runner
        """
        logger.info(f"Stickytape the runner template for dependency resolution")
        runner_file_path = fn_dir / f"{runner_filename}.py"
        os.system(f"stickytape {temp_runner_path} > {runner_file_path}")

        logger.info(f"Deleting temporary runner")
        os.remove(temp_runner_path)

        logger.info(f"Successfully created build directory for function {fn_name}")

    """
    NOTE - statemachine parameters
    """

    def __get_statemachine_params(self):
        statemachinename = self.__user_dag.get_user_dag_name()
        params = {
            "name": statemachinename,
            "uri": self.__json_file,
            "arn": statemachinename + "Arn",
            "role": statemachinename + "Role",
            "role_arn": statemachinename + "RoleArn",
            "arn_attribute": statemachinename + ".Arn",
            "api_file": "api.yaml",
        }

        role_arn_attribute = params["role"] + ".Arn"
        params["role_arn_attribute"] = role_arn_attribute
        return params

    def __template_function_id(self, runner_template_dir, function_id, function_name, function_runner_filename):
        # runner_template_filename = f"runner_template_{function_name}.py"
        runner_template_filename = function_runner_filename
        try:
            file_loader = FileSystemLoader(runner_template_dir)
            env = Environment(loader=file_loader)
            template = env.get_template("runner_template.py")
            logger.info(
                f"Created jinja2 environement for templating AWS function ids for function::{function_name}"
            )
        except:
            raise Exception(
                f"Unable to load environment for AWS function id templating for function::{function_name}"
            )

        # render the template
        try:
            output = template.render(function_id_placeholder=function_id)
            with open(f"{runner_template_dir}/{runner_template_filename}", "w") as out:
                out.write(output)
                logger.info(
                    f"Rendered and flushed the runner template for AWS function for function::{function_name}"
                )
        except Exception as e:
            logger.error(e)
            raise Exception(
                f"Unable to render the function runner template for AWS function for function::{function_name}"
            )

        return runner_template_filename

    '''
    Function to append xfaas dependencies to the function requirements
    '''
    def __append_xfaas_default_requirements(self, filepath):
        with open(filepath, "r") as file:
            lines = file.readlines()
            lines.append("psutil\n")
            lines.append("objsize\n")
            unqiue_dependencies = set(lines)
            file.flush()
            
        with open(filepath, "w") as file:
            for line in [x.strip("\n") for x in sorted(unqiue_dependencies)]:
                file.write(f"{line}\n")

    """
    Create standalone runner templates
    """

    def __create_standalone_runners(self, xfaas_fn_build_dir):
        function_metadata_list = self.__user_dag.get_node_param_list()
        function_object_map = self.__user_dag.get_node_object_map()

        for function_metadata in function_metadata_list:
            function_name = function_metadata["name"]
            function_runner_filename = function_object_map[
                function_metadata["name"]
            ].get_runner_filename()
            function_path = function_object_map[function_metadata["name"]].get_path()

            function_module_name = function_object_map[
                function_metadata["name"]
            ].get_module_name()
            function_id = function_object_map[function_metadata["name"]].get_id()

            # template the function runner template in the runner template directory
            runner_template_filename = self.__template_function_id(
                runner_template_dir=self.__runner_template_dir,
                function_id=function_id,
                function_name=function_name,
                function_runner_filename=function_runner_filename
            )

            logger.info(
                f"Starting Standalone Runner Creation for function {function_name}"
            )

            self.__create_lambda_fns(
                self.__parent_directory_path / function_path,
                # self.__aws_build_dir,
                xfaas_fn_build_dir,
                function_name,
                function_module_name,
                function_runner_filename,
                self.__runner_template_dir,
                # self.__serwo_utils_dir,
                runner_template_filename
            )

            runner_template_filepath = (
                self.__runner_template_dir / runner_template_filename
            )
            logger.info(
                f"Deleting Temporary Runner Template at {runner_template_filepath}"
            )
            os.remove(f"{runner_template_filepath}")   
    def __generate_asl_template(self):
        function_metadata_list = self.__user_dag.get_node_param_list()
        function_object_map = self.__user_dag.get_node_object_map()
        statemachine = self.__get_statemachine_params()
        statemachine_structure = self.__user_dag.get_statemachine_structure()

        try:
            AWSSfnYamlGenerator.generate_sfn_yaml(
                function_metadata_list,
                statemachine,
                function_object_map,
                self.__yaml_template_dir,
                self.__aws_build_dir,
                self.__yaml_file,
                self.__trigger_type,
            )
        except Exception as e:
            logger.error(e)
            traceback.print_exc()
            exit()

        logger.info("Building Statemachines JSON..")
        sfn_json=AWSSfnAslBuilder.generate_statemachine_json(
            statemachine_structure, self.__aws_build_dir, self.__json_file
        )
        dag_json=self.__user_dag.get_user_dag_nodes()
        list_async_fns= get_set_of_async_funtions(dag_json)
        print("List of Async Fns:",list_async_fns)
        changing_fns=set()
        for node_name in list_async_fns:
            successors = self.__user_dag.get_successor_node_names(node_name)
            for fn_name in successors:
                changing_fns.add(fn_name)

        print("Set of changing funtions:",changing_fns)
        changing_fns_list=list(changing_fns)
        print("List of changing funtions:",changing_fns_list)
        # Statemachine.asl.josn should be changed here
        sfn_json_copy = copy.deepcopy(json.loads(sfn_json))
        data=add_async_afn_builder(sfn_json_copy,changing_fns_list)
        print("Updated data of sfn builder after adding poll",data)
        with open(f"{self.__aws_build_dir}/{self.__json_file}", "w") as statemachinejson:
            statemachinejson.write(json.dumps(data))
        print("sucessfully written data into the file")
    """
    NOTE - build function
    """

    def build_resources(self):
        logger.info(f"Creating environment for {self.__user_dag.get_user_dag_name()}")
        xfaas_fn_build_dir = self.__create_environment()

        logger.info(
            f"Initating standalone runner creation for {self.__user_dag.get_user_dag_name()}"
        )
        self.__create_standalone_runners(xfaas_fn_build_dir)

        logger.info(
            f"Generating ASL templates for {self.__user_dag.get_user_dag_name()}, \
                     AWS Stack - {self.__sam_stackname}"
        )
        self.__generate_asl_template()

        logger.info("Adding API specification to user directory")
        shutil.copyfile(
            src=self.__yaml_template_dir / "execute-api-openapi.yaml",
            dst=self.__aws_build_dir / self.__get_statemachine_params()["api_file"],
        )

        logger.info("Creating SAM build directory")
        if not os.path.exists(self.__sam_build_dir):
            try:
                os.makedirs(self.__sam_build_dir)
            except Exception as e:
                logger.error(e)
                traceback.print_exc()
                exit()

        logger.info("Creating resource directory for AWS stack output")
        if not os.path.exists(self.__serwo_resources_dir):
            try:
                os.makedirs(self.__serwo_resources_dir)
            except Exception as e:
                logger.error(e)
                traceback.print_exc()
                exit()

    """
    NOTE - build workflow
    """

    def build_workflow(self):
        logger.info(f"Starting SAM Build for {self.__user_dag.get_user_dag_name()}")
        os.system(
            f"sam build --build-dir {self.__sam_build_dir} --template-file {self.__aws_build_dir / self.__yaml_file}"
        )

    """
    NOTE - deploy workflow
    """

    def deploy_workflow(self):
        logger.info(f"Starting SAM Deploy for {self.__user_dag.get_user_dag_name()}")
        os.system(
            f"sam deploy \
              --template-file {self.__sam_build_dir / self.__yaml_file} \
              --stack-name {self.__sam_stackname} \
              --region {self.__region} \
              --capabilities CAPABILITY_IAM \
              --no-confirm-changeset \
              --resolve-image-repos \
              --disable-rollback \
              --resolve-s3"
        )

        logger.info(f"Writing SAM outputs to .. {self.__outputs_filepath}")
        os.system(
            f'aws cloudformation describe-stacks \
            --stack-name {self.__sam_stackname} \
            --region {self.__region} \
            --query "Stacks[0].Outputs" \
            --output json > {self.__outputs_filepath}'
        )

        ## add sam stack name to ouput filepat
        with open(self.__outputs_filepath, "r") as f:
            data = json.load(f)
        data.append({"OutputKey": "SAMStackName", "OutputValue": self.__sam_stackname, "Description": "SAM Stack Name"})
        with open(self.__outputs_filepath, "w") as f:
            json.dump(data, f, indent=4)

        return self.__outputs_filepath

def add_async_afn_builder(data,list):

    for i in range(0,len(list)):
        fn_name=list[i]
        poll_next=data["States"][fn_name]['Next']
        checkPollcondition='CheckPollCondition'+str(i)
        waitstate='WaitState'+str(i)
        data["States"][fn_name]['Next']=checkPollcondition
        data[checkPollcondition]={
                "Type": "Choice",
                "Choices": [
                    {
                        "Variable": "$.body.Poll",
                        "BooleanEquals": False,
                        "Next": poll_next
                    }
                ],
                "Default": waitstate
            }
        data[waitstate]={
                "Type": "Wait",
                "Seconds": 900,
                "Next": fn_name
            }
    return data


def get_set_of_async_funtions(fns_data):
    print("Funtions data:",(fns_data))
    # fns_data=json.loads(fns_data)
    list_async_fun=[]
    for node in fns_data:
        if "IsAsync" in node and node["IsAsync"]:
            node_name=node["NodeName"]
            list_async_fun.append(node_name)
    return list_async_fun