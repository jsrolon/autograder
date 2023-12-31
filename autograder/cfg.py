import datetime
import os
import pathlib

import dateparser
import dotenv
import yaml

from env_flag import env_flag

# load from env file
autograder_env_path = pathlib.Path.home() / ".autograder.env"
if autograder_env_path.exists():
    dotenv.load_dotenv(dotenv_path=autograder_env_path)

# define exports
MJ_USERNAME = os.getenv("MJ_USERNAME")
MJ_PASSWORD = os.getenv("MJ_PASSWORD")

AUTOGRADER_WORKING_DIR = os.getenv("AUTOGRADER_WORKING_DIR", default=str(pathlib.Path.home()))
AUTOGRADER_TARGET_ONLY = os.getenv("AUTOGRADER_TARGET_ONLY")
AUTOGRADER_LOG_MAX_FILES = os.getenv("AUTOGRADER_LOG_MAX_FILES", 7)
AUTOGRADER_GITLAB_TOKEN = os.getenv("AUTOGRADER_GITLAB_TOKEN")
AUTOGRADER_CLONE_BRANCH = os.getenv("AUTOGRADER_CLONE_BRANCH", "main")

AUTOGRADER_DISABLE_DEADLINE = env_flag("AUTOGRADER_DISABLE_DEADLINE")
deadline_val = os.getenv("AUTOGRADER_DEADLINE_VAL")
if deadline_val:
    AUTOGRADER_DEADLINE_VAL = dateparser.parse(deadline_val)
else:
    AUTOGRADER_DEADLINE_VAL = datetime.date.today()

AUTOGRADER_BASE_REPO = os.getenv("AUTOGRADER_GITLAB_BASE_REPO", default="balmau/comp310-winter23")
AUTOGRADER_BASE_REPO_CLONE_LOCATION = f"{AUTOGRADER_WORKING_DIR}/repos/{AUTOGRADER_BASE_REPO}"
AUTOGRADER_BASE_REPO_CLONE_PATH = pathlib.Path(AUTOGRADER_BASE_REPO_CLONE_LOCATION)
AUTOGRADER_BASE_REPO_BRANCH = os.getenv("AUTOGRADER_BASE_REPO_BRANCH", default="main")
AUTOGRADER_SPECIFIC_COMMIT = os.getenv("AUTOGRADER_SPECIFIC_COMMIT")

AUTOGRADER_USE_LOCAL_COPY = env_flag("AUTOGRADER_USE_LOCAL_COPY")

AUTOGRADER_REPORT_PATH = pathlib.Path(f"{AUTOGRADER_WORKING_DIR}/reports/")

now = datetime.datetime.now()
AUTOGRADER_TEST_OUTPUTS_PATH = pathlib.Path(f"{AUTOGRADER_WORKING_DIR}/test_outputs/{now.strftime('%Y%m%d%H%M%S')}")

DEBUG = env_flag("DEBUG")
CAPTURE_OUTPUT = env_flag("CAPTURE_OUTPUT")
if not CAPTURE_OUTPUT:
    CAPTURE_OUTPUT = not DEBUG

GITLAB_URL = os.getenv("AUTOGRADER_GITLAB_URL", "gitlab.cs.mcgill.ca")

with open(f"{os.path.dirname(__file__)}/resources/mapping.yaml", "r") as f:
    FORKS = yaml.safe_load(f)

with open(f"{os.path.dirname(__file__)}/resources/order_matters.yml", "r") as f:
    ORDER_MATTERS = yaml.safe_load(f)

with open(f"{os.path.dirname(__file__)}/resources/run_multiple.yml", "r") as f:
    RUN_MULTIPLE = yaml.safe_load(f)

AUTOGRADER_MT_ITERATIONS = int(os.getenv("AUTOGRADER_MT_ITERATIONS", default=10))

deadline_str = AUTOGRADER_DEADLINE_VAL.strftime("%d%b%Y")
AUTOGRADER_CSV_REPORT_FILE = open(f"{AUTOGRADER_WORKING_DIR}/report_{deadline_str}.csv", 'w')


def autograder_make_command_line(frame_sz=18, var_sz=10):
    return ["make", "CC=gcc-11", f"framesize={frame_sz}", f"varmemsize={var_sz}"]
