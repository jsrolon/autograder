import logging
import os
from typing import List

from mailjet_rest import Client

from autograder import cfg

mailjet = Client(
    auth=(cfg.MJ_USERNAME, cfg.MJ_PASSWORD),
    version='v3.1')


def mj_send_email(to, body, id):
    sandbox = cfg.DEBUG

    to_list = list(map(lambda addr: {"Email": addr}, to))
    data = {
        'Messages': [
            {
                "From": {
                    "Email": os.getenv("AUTOGRADER_EMAIL_FROM_ADDR", default="sebastian.rolon@mcgill.ca"),
                    "Name": "COMP310 Autograder"
                },
                "To": to_list,
                "Subject": "COMP310 Autograder Report",
                "TextPart": body,
            }
        ],
        'SandboxMode': sandbox
    }
    result = mailjet.send.create(data=data)
    if result.status_code == 200:
        logging.info(f"(SANDBOX {sandbox}) Sent email to {id} members {to}")
    else:
        logging.error(f"Email sending to {id} members {to} failed with status {result.status_code}")


RETURN_CODES = {
    132: "Illegal operation (SIGILL)",
    133: "Program aborted (SIGTRAP)",
    134: "Program aborted (SIGABRT)",
    136: "Program aborted (SIGFPE)",
    137: "Too much memory",
    138: "Program aborted (SIGBUS)",
    139: "Segmentation fault (SIGSEGV)"
}


class Reporter:
    PASS = "PASS"
    FAIL = "FAIL"
    TIMEOUT = "TIMEOUT"

    _mailjet = None
    _emails = None

    _reporters = {}

    @staticmethod
    def get_reporter(project_identifier: str):
        return Reporter._reporters[project_identifier]

    def __init__(self, project_name: str):
        # self._emails = emails

        self.project_name = project_name
        self.message_buffer = []

        self.message_buffer.append(f"COMP310 AUTOGRADER REPORT FOR {project_name}")

        Reporter._reporters[project_name] = self

    def append(self, message: str):
        self.message_buffer.append(message)

    def succeed(self, test_name: str):
        self.message_buffer.append(f"# {test_name:<25} {self.PASS}")

    def fail(self, test_name: str):
        self.message_buffer.append(f"# {test_name:<25} {self.FAIL}")

    def timeout(self, test_name: str):
        self.message_buffer.append(f"# {test_name:<25} {self.TIMEOUT}")

    def exit_code(self, test_name: str, exit_code: int):
        if exit_code in RETURN_CODES:
            self.message_buffer.append(f"# {test_name:<25} {RETURN_CODES[exit_code]}")
        else:
            self.message_buffer.append(f"# {test_name:<25} Abnormal exit code {exit_code}")

    def send_email(self):
        full_message_body = "\n".join(self.message_buffer)
        if cfg.DEBUG:
            print(full_message_body)

        if self.project_name in cfg.FORKS:
            mj_send_email(cfg.FORKS[self.project_name], full_message_body, self.project_name)
            with open(f"{cfg.AUTOGRADER_WORKING_DIR}/{self.project_name.split('/')[0]}.txt", 'w') as f:
                f.write(full_message_body)
                f.close()
        else:
            logging.error(f"No emails found for {self.project_name}")
