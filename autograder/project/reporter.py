import logging
import os
from typing import List

from mailjet_rest import Client

from autograder import cfg

mailjet = Client(
    auth=(cfg.MJ_USERNAME, cfg.MJ_PASSWORD),
    version='v3.1')


def mj_send_email(to, body, id):
    # sandbox = cfg.DEBUG # TODO: change this on release
    sandbox = True

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

    def send_email(self):
        full_message_body = "\n".join(self.message_buffer)
        mj_send_email(cfg.FORKS[self.project_name], full_message_body, self.project_name)
