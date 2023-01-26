import os
import pathlib
import dotenv

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
AUTOGRADER_GITLAB_BASE_REPO_ID = os.getenv("AUTOGRADER_GITLAB_BASE_REPO_ID", default=795)
AUTOGRADER_GITLAB_TOKEN = os.getenv("AUTOGRADER_GITLAB_TOKEN")
AUTOGRADER_CLONE_BRANCH = os.getenv("AUTOGRADER_CLONE_BRANCH", "main")
AUTOGRADER_DISABLE_DEADLINE = env_flag("AUTOGRADER_DISABLE_DEADLINE")

DEBUG = env_flag("DEBUG")
capture_output = os.getenv("CAPTURE_OUTPUT")
if capture_output:
    CAPTURE_OUTPUT = capture_output
else:
    CAPTURE_OUTPUT = not DEBUG

GITLAB_URL = os.getenv("AUTOGRADER_GITLAB_URL", "gitlab.cs.mcgill.ca")
