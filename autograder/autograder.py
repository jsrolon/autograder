import logging
import logging.handlers
import os
import subprocess
import multiprocessing
import pathlib
import sys
import shutil

import gitlab
import dotenv

from .project import test_runner, reporter

AUTOGRADER_WORKING_DIR = os.getenv("AUTOGRADER_WORKING_DIR", default=str(pathlib.Path.home()))
CAPTURE_OUTPUT = os.getenv("DEBUG") != "1"
DEBUG = os.getenv("DEBUG") == "1"

GITLAB_URL = os.getenv("AUTOGRADER_GITLAB_URL", "gitlab.cs.mcgill.ca")


def main():
    set_up_logging()
    load_env()
    forks = get_forks()
    logging.info(f"Found {len(forks)} forks of main project, starting autograding...")

    with multiprocessing.Pool() as p:
        p.map(process_project, forks)
        logging.info("Autograder completed.")


def set_up_logging():
    handler_list = []
    trfh = logging.handlers.TimedRotatingFileHandler(
        filename=pathlib.Path(AUTOGRADER_WORKING_DIR, "autograder.log"),
        backupCount=int(os.getenv("AUTOGRADER_LOG_MAX_FILES", 7)),
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
        logging.info("env loaded successfully")
    else:
        logging.warning(
            f"Env file {autograder_env_path} not found, proceeding with default values. Autograder may not work.")


def get_forks():
    gitlab_token = os.getenv("AUTOGRADER_GITLAB_TOKEN")
    if gitlab_token is None:
        logging.error("Gitlab token not provided, cannot proceed.")
        sys.exit(1)

    gl = gitlab.Gitlab(url=f"https://{GITLAB_URL}", private_token=gitlab_token)
    logging.info("Gitlab authentication successful")
    base_project = gl.projects.get(os.getenv("AUTOGRADER_GITLAB_BASE_REPO_ID", default=795))
    forks = base_project.forks.list()
    return forks


def process_project(project):
    project_identifier = project.namespace['path']
    logging.debug(f"Beggining processing for '{project_identifier}'")
    rep = reporter.Reporter(project_identifier)

    clone_location = f"{AUTOGRADER_WORKING_DIR}/repos/{project.path_with_namespace}"
    src_location = f"{clone_location}/src"
    try:
        update_local_repo(clone_location, project)
    except Exception as e:
        logging.error(f"Error cloning {project_identifier}, stopping processing")
        logging.exception(e)
        return

    completed_make = subprocess.run(["make"], cwd=src_location,
                                    capture_output=CAPTURE_OUTPUT)
    rep.append(f"# Compilation {'PASS' if completed_make.returncode == 0 else 'FAILED'}")
    if completed_make.returncode == 0:
        test_runner.TestRunner(project_identifier, pathlib.Path(clone_location)).run_all()

    rep.send_email()


def update_local_repo(clone_location: str, project):
    if os.path.isdir(clone_location):
        shutil.rmtree(clone_location)

    gitlab_token = os.getenv("AUTOGRADER_GITLAB_TOKEN")
    branch_to_clone = os.getenv("AUTOGRADER_CLONE_BRANCH", "main")
    clone_result = subprocess.run(
        ["git", "clone", "--depth=1", f"--branch={branch_to_clone}", "--single-branch",
         f"https://oauth2:{gitlab_token}@{GITLAB_URL}/{project.path_with_namespace}.git", clone_location],
        capture_output=CAPTURE_OUTPUT)
    if clone_result.returncode != 0:
        raise Exception(f"Git clone failed with status code {clone_result.returncode}")
