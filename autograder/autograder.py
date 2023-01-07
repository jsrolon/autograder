import logging
import logging.handlers
import os
import subprocess
import multiprocessing
import pathlib
import sys
import shutil
import pytz
from datetime import datetime, date

import gitlab
import dotenv

from .project import test_runner, reporter


class Autograder:
    AUTOGRADER_WORKING_DIR = os.getenv("AUTOGRADER_WORKING_DIR", default=str(pathlib.Path.home()))
    CAPTURE_OUTPUT = os.getenv("DEBUG") != "1"
    DEBUG = os.getenv("DEBUG") == "1"

    GITLAB_URL = os.getenv("AUTOGRADER_GITLAB_URL", "gitlab.cs.mcgill.ca")

    _gitlab = None
    _gitlab_token = None

    def main(self):
        self.set_up_logging()
        self.load_env()
        forks = self.get_forks()
        logging.info(f"Found {len(forks)} forks of main project, starting autograding...")

        with multiprocessing.Pool() as p:
            p.map(self.process_project, forks)
            logging.info("Autograder completed.")

    def set_up_logging(self):
        handler_list = []
        trfh = logging.handlers.TimedRotatingFileHandler(
            filename=pathlib.Path(self.AUTOGRADER_WORKING_DIR, "autograder.log"),
            backupCount=int(os.getenv("AUTOGRADER_LOG_MAX_FILES", 7)),
            when='d')
        if self.DEBUG:
            handler_list = None
        else:
            handler_list.append(trfh)
        logging.basicConfig(format='%(asctime)s %(levelname)s %(filename)s %(message)s',
                            level=logging.INFO,
                            handlers=handler_list)

    def load_env(self):
        autograder_env_path = pathlib.Path.home() / ".autograder.env"
        if autograder_env_path.exists():
            dotenv.load_dotenv(dotenv_path=autograder_env_path)
            logging.info("env loaded successfully")
        else:
            logging.warning(
                f"Env file {autograder_env_path} not found, proceeding with default values. Autograder may not work.")

    def get_forks(self):
        self._gitlab_token = os.getenv("AUTOGRADER_GITLAB_TOKEN")
        if self._gitlab_token is None:
            logging.error("Gitlab token not provided, cannot proceed.")
            sys.exit(1)

        self._gitlab = gitlab.Gitlab(url=f"https://{self.GITLAB_URL}", private_token=self._gitlab_token)
        logging.info("Gitlab authentication successful")
        base_project = self._gitlab.projects.get(os.getenv("AUTOGRADER_GITLAB_BASE_REPO_ID", default=795))
        forks = list(map(lambda fork: self._gitlab.projects.get(fork.id), base_project.forks.list()))
        return forks

    def process_project(self, project):
        project_identifier = project.path_with_namespace

        emails = []
        members = project.members.list()
        for member in members:
            usr = self._gitlab.users.get(member.id)
            emails.append(usr.attributes["public_email"])

        if not emails or not emails[0]:
            logging.info(f"No project members in {project_identifier} have public emails, no point in reporting")
            return

        logging.debug(f"Beggining processing for '{project_identifier}'")
        rep = reporter.Reporter(project_identifier, emails)

        clone_location = f"{self.AUTOGRADER_WORKING_DIR}/repos/{project.path_with_namespace}"
        src_location = f"{clone_location}/src"
        try:
            self.update_local_repo(clone_location, project)
        except Exception as e:
            logging.error(f"Error cloning {project_identifier}, stopping processing")
            logging.exception(e)
            return

        completed_make = subprocess.run(["make"], cwd=src_location,
                                        capture_output=self.CAPTURE_OUTPUT)
        rep.append(f"# Compilation {'PASS' if completed_make.returncode == 0 else 'FAILED'}")
        if completed_make.returncode == 0:
            test_runner.TestRunner(project_identifier, pathlib.Path(clone_location)).run_all()

        rep.send_email()

    def update_local_repo(self, clone_location: str, project):
        if os.path.isdir(clone_location):
            shutil.rmtree(clone_location)

        branch_to_clone = os.getenv("AUTOGRADER_CLONE_BRANCH", "main")
        clone_result = subprocess.run(
            ["git", "clone", f"--branch={branch_to_clone}", "--single-branch",
             f"https://oauth2:{self._gitlab_token}@{self.GITLAB_URL}/{project.path_with_namespace}.git", clone_location],
            capture_output=self.CAPTURE_OUTPUT)
        if clone_result.returncode != 0:
            raise Exception(f"Git clone failed with status code {clone_result.returncode}")

        # obtain last commit id before deadline
        deadline_naive = datetime.combine(date.today(), datetime.min.time())
        deadline_mtl = pytz.timezone('America/Toronto').localize(deadline_naive)
        deadline_mtl_unix = int(deadline_mtl.timestamp())
        last_commit_id_output = subprocess.check_output([
            "git", "log", f"--before={deadline_mtl_unix}", "--pretty=format:'%H'"],
            cwd=clone_location,
            encoding='utf-8')
        last_commit_id = last_commit_id_output.replace("'", "").splitlines()[0]

        # checkout to that commit
        checkout_result = subprocess.run(
            ["git", "checkout", last_commit_id],
            cwd=clone_location,
            capture_output=self.CAPTURE_OUTPUT)
        if checkout_result.returncode != 0:
            raise Exception(f"Git checkout failed with status code {clone_result.returncode}")
