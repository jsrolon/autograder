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

CAPTURE_OUTPUT = env_flag("DEBUG")
DEBUG = env_flag("DEBUG")

GITLAB_URL = os.getenv("AUTOGRADER_GITLAB_URL", "gitlab.cs.mcgill.ca")
