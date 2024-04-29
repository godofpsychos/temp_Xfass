from qxfaas_plot_class import QXFBenchPlotter
import argparse


parser = argparse.ArgumentParser(
    prog="ProgramName",
    description="What the program does",
    epilog="Text at the bottom of help",
)

parser.add_argument("--wfdir",dest='wfdir',type=str,help="Workflow Directory")
parser.add_argument("--deployment-id",dest='wf_deployment_id',type=str,help="Deployment Id")
parser.add_argument("--artifacts-filepath",dest='artifacts_filepath',type=str,help="Artifacts Filepath")

run_id="test"
format=".pdf"

if __name__ == "__main__":
    args = parser.parse_args()
    user_wf_dir = args.wfdir
    wf_deployment_id = args.wf_deployment_id
    artifacts_filepath = args.artifacts_filepath
    plotter = QXFBenchPlotter(user_wf_dir, wf_deployment_id, run_id,format, artifacts_filepath)
    plotter.plot_stagewise(yticks=[],figwidth=20)
    