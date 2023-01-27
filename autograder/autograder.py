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
    _gitlab_autograder_user_id = None

    def main(self):
        self.set_up_logging()
        self.update_local_repo(cfg.AUTOGRADER_BASE_REPO_CLONE_LOCATION, cfg.AUTOGRADER_BASE_REPO)
        forks = cfg.FORKS.keys()
        logging.info(f"Found {len(forks)} forks of main project, starting autograding...")

        with ThreadPool() as p:
            p.map(self.process_project, forks)
            logging.info("Autograder completed.")

    def set_up_logging(self):
        urllib3_logger = logging.getLogger("urllib3")
        urllib3_logger.setLevel(logging.ERROR)

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

    def process_project(self, project):
        logging.debug(f"Beggining processing for '{project}'")
        rep = reporter.Reporter(project)

        clone_location = f"{cfg.AUTOGRADER_WORKING_DIR}/repos/{project}"
        could_clone = False
        try:
            self.update_local_repo(clone_location, project)
            could_clone = True
        except Exception:
            rep.append(f"The autograder couldn't clone your repo. Did you add @jrolon with Reporter access?")
            logging.error(f"Error cloning {project} into {clone_location}, stopping processing")

        if could_clone:
            src_location = f"{clone_location}/src"
            if not os.path.isdir(src_location):
                rep.append(f"Expected repository structure not found. Did you fork the coursework repo?")
            else:
                completed_make = subprocess.run(["make"], cwd=src_location,
                                                capture_output=cfg.CAPTURE_OUTPUT)
                rep.append(f"# Compilation {'PASS' if completed_make.returncode == 0 else 'FAILED'}")
                if completed_make.returncode == 0:
                    test_runner.TestRunner(project, pathlib.Path(clone_location)).run_all()

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
             f"https://oauth2:{cfg.AUTOGRADER_GITLAB_TOKEN}@{cfg.GITLAB_URL}/{project}.git", clone_location],
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
