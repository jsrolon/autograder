import logging
import logging.handlers
import os
import subprocess
import multiprocessing
import pathlib

import gitlab
import dotenv

from . import test_runner, reporter


AUTOGRADER_WORKING_DIR = os.getenv("AUTOGRADER_WORKING_DIR", default=str(pathlib.Path.home()))
CAPTURE_OUTPUT = os.getenv("DEBUG") != "1"
DEBUG = os.getenv("DEBUG") == "1"


def main():
    set_up_logging()
    load_env()

    gl = gitlab.Gitlab(url="https://gitlab.cs.mcgill.ca", private_token=os.getenv("AUTOGRADER_GITLAB_TOKEN"))
    logging.info("Gitlab authentication successful")

    base_project = gl.projects.get(os.getenv("AUTOGRADER_GITLAB_BASE_REPO_ID", default=795))
    forks = base_project.forks.list()
    logging.info(f"Found {len(forks)} forks of main project, starting autograding...")

    with multiprocessing.Pool() as p:
        p.map(process_project, forks)
        logging.info("Autograder completed.")


def set_up_logging():
    handler_list = []
    trfh = logging.handlers.TimedRotatingFileHandler(
        filename=pathlib.Path(AUTOGRADER_WORKING_DIR, "autograder.log"),
        when='d')
    if DEBUG:
        handler_list = None
    else:
        handler_list.append(trfh)
    logging.basicConfig(format='%(asctime)s %(levelname)s %(filename)s %(message)s',
                        level=logging.INFO,
                        handlers=handler_list)


def load_env():
    autograder_env_path = pathlib.Path.home() / ".autograder.env"
    if autograder_env_path.exists():
        dotenv.load_dotenv(dotenv_path=autograder_env_path)
    else:
        logging.warning(
            "Env file ~/.autograder.env not found, proceeding with default values. Autograder may not work.")


def process_project(project):
    project_identifier = project.namespace['path']
    logging.debug(f"Beggining processing for '{project_identifier}'")
    rep = reporter.Reporter(project_identifier)

    clone_location = f"{AUTOGRADER_WORKING_DIR}/repos/{project.path_with_namespace}"
    src_location = f"{clone_location}/src"
    update_local_repo(clone_location, project)

    completed_make = subprocess.run(["make"], cwd=src_location,
                                    capture_output=CAPTURE_OUTPUT)
    rep.append(f"# Compilation {'PASS' if completed_make.returncode == 0 else 'FAILED'}")
    if completed_make.returncode == 0:
        test_runner.TestRunner(project_identifier, pathlib.Path(clone_location)).run_all()

    rep.send()


def update_local_repo(clone_location, project):
    try:
        os.makedirs(clone_location)
        subprocess.run(
            ["git", "clone", "--depth=1", "--branch=main", "--single-branch", project.ssh_url_to_repo, clone_location],
            capture_output=CAPTURE_OUTPUT)
    except FileExistsError:
        subprocess.run(["git", "pull"], cwd=clone_location, capture_output=CAPTURE_OUTPUT)
        subprocess.run(["git", "clean", "-d", "--force"], cwd=clone_location, capture_output=CAPTURE_OUTPUT)
