import logging
import logging.handlers
import os
import subprocess
from multiprocessing.pool import ThreadPool
import pathlib
import sys
import shutil
import pytz
from datetime import datetime, date

import gitlab

from autograder import cfg
from autograder.project import reporter, test_runner


class Autograder:
    _gitlab = None
    _gitlab_token = None

    def main(self):
        self.set_up_logging()
        self.set_up_gitlab()
        target_only = cfg.AUTOGRADER_TARGET_ONLY
        if target_only:
            logging.info(f"Running autograder in single target mode for project {target_only}")
            forks = [self._gitlab.projects.get(target_only)]
        else:
            forks = self.get_forks()
        logging.info(f"Found {len(forks)} forks of main project, starting autograding...")

        with ThreadPool() as p:
            p.map(self.process_project, forks)
            logging.info("Autograder completed.")

    def set_up_logging(self):
        handler_list = []
        trfh = logging.handlers.TimedRotatingFileHandler(
            filename=pathlib.Path(cfg.AUTOGRADER_WORKING_DIR, "autograder.log"),
            backupCount=int(cfg.AUTOGRADER_LOG_MAX_FILES),
            when='d')
        if cfg.DEBUG:
            handler_list = None
        else:
            handler_list.append(trfh)
        logging.basicConfig(format='%(asctime)s %(levelname)s %(filename)s %(message)s',
                            level=logging.INFO,
                            handlers=handler_list)

    def get_forks(self):
        base_project = self._gitlab.projects.get(cfg.AUTOGRADER_GITLAB_BASE_REPO_ID)
        forks = list(map(lambda fork: self._gitlab.projects.get(fork.id), base_project.forks.list(get_all=True)))
        return forks

    def set_up_gitlab(self):
        self._gitlab_token = cfg.AUTOGRADER_GITLAB_TOKEN
        if self._gitlab_token is None:
            logging.error("Gitlab token not provided, cannot proceed.")
            sys.exit(1)
        self._gitlab = gitlab.Gitlab(url=f"https://{cfg.GITLAB_URL}", private_token=self._gitlab_token)
        logging.info("Gitlab authentication successful")

    def process_project(self, project):
        project_identifier = project.path_with_namespace

        emails = []
        members = project.members.list()
        for member in members:
            if member.access_level >= 40:  # only collect mantainers and above
                usr = self._gitlab.users.get(member.id)
                email = usr.attributes["public_email"]
                if email:  # some accounts have empty public emails
                    emails.append(email)

        if not emails or not emails[0]:
            logging.info(f"No project members in {project_identifier} have public emails, no point in reporting")
            return

        logging.debug(f"Beggining processing for '{project_identifier}'")
        rep = reporter.Reporter(project_identifier, emails)

        clone_location = f"{cfg.AUTOGRADER_WORKING_DIR}/repos/{project.path_with_namespace}"
        src_location = f"{clone_location}/src"
        try:
            self.update_local_repo(clone_location, project)
        except Exception:
            logging.error(f"Error cloning {project_identifier} into {clone_location}, stopping processing")
            return

        completed_make = subprocess.run(["make"], cwd=src_location,
                                        capture_output=cfg.CAPTURE_OUTPUT)
        rep.append(f"# Compilation {'PASS' if completed_make.returncode == 0 else 'FAILED'}")
        if completed_make.returncode == 0:
            test_runner.TestRunner(project_identifier, pathlib.Path(clone_location)).run_all()

        rep.send_email()

    def update_local_repo(self, clone_location: str, project):
        if os.path.isdir(clone_location):
            # apparently some students' code creates directories without read access, so we ensure rwx permissions
            completed_chown = subprocess.run(["chmod", "-R", "744", clone_location], capture_output=cfg.CAPTURE_OUTPUT)
            if completed_chown.returncode != 0:
                logging.warning(f"Could not change dir permissions on {clone_location}, clone may fail")
            shutil.rmtree(clone_location)

        branch_to_clone = cfg.AUTOGRADER_CLONE_BRANCH
        clone_result = subprocess.run(
            ["git", "clone", f"--branch={branch_to_clone}", "--single-branch",
             f"https://oauth2:{self._gitlab_token}@{cfg.GITLAB_URL}/{project.path_with_namespace}.git", clone_location],
            capture_output=cfg.CAPTURE_OUTPUT, text=True)
        if clone_result.returncode != 0:
            if clone_result.stderr:
                logging.error(f"{clone_result.stderr}")
            raise Exception(f"Git clone failed with status code {clone_result.returncode}")

        if cfg.AUTOGRADER_DISABLE_DEADLINE:
            return
        else:
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
                capture_output=cfg.CAPTURE_OUTPUT)
            if checkout_result.returncode != 0:
                raise Exception(f"Git checkout failed with status code {clone_result.returncode}")
