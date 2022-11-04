import logging
import logging.handlers
import os
import subprocess
import multiprocessing
import pathlib

import gitlab

from . import test_runner, reporter

AUTOGRADER_WORKING_DIR = "/tmp"
CAPTURE_OUTPUT = True

logging.basicConfig(format='%(asctime)s %(levelname)s %(filename)s %(message)s', level=logging.INFO)


def process_project(project):
    project_identifier = project.namespace['path']

    logging.debug(f"Beggining processing for '{project_identifier}'")
    rep = reporter.Reporter(project_identifier)

    clone_location = f"{AUTOGRADER_WORKING_DIR}/repos/{project.path_with_namespace}"
    src_location = f"{clone_location}/src"
    try:
        os.makedirs(clone_location)
        subprocess.run(
            ["git", "clone", "--depth=1", "--branch=main", "--single-branch", project.ssh_url_to_repo, clone_location],
            capture_output=CAPTURE_OUTPUT)
    except FileExistsError:
        subprocess.run(["git", "pull"], cwd=clone_location, capture_output=CAPTURE_OUTPUT)
        subprocess.run(["git", "clean", "-d", "--force"], cwd=clone_location, capture_output=CAPTURE_OUTPUT)

    completed_make = subprocess.run(["make"], cwd=src_location,
                                    capture_output=CAPTURE_OUTPUT)
    rep.append(f"# {'Compilation':<25} {'OK' if completed_make.returncode == 0 else 'FAILED'}")
    if completed_make.returncode == 0:
        test_runner.TestRunner(project_identifier, pathlib.Path(clone_location)).run_all()

    rep.send()


def main():
    gl = gitlab.Gitlab(url="https://gitlab.cs.mcgill.ca", private_token=os.environ["AUTOGRADER_GITLAB_TOKEN"])
    logging.info("Gitlab authentication successful")

    base_project = gl.projects.get(795)
    forks = base_project.forks.list()
    logging.info(f"Found {len(forks)} forks of main project, starting autograding...")

    with multiprocessing.Pool() as p:
        p.map(process_project, forks)
