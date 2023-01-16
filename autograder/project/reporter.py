import logging
import smtplib
import os
from email.message import EmailMessage
import pathlib

import yaml
from typing import List

from mailjet_rest import Client

mailjet = Client(
    auth=(os.getenv("MJ_USERNAME"), os.getenv("MJ_PASSWORD")),
    version='v3.1')


def send_email(to, body):
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
        ]
    }
    mailjet.send.create(data=data)


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

    def __init__(self, project_name: str, emails: List[str]):
        self._emails = emails

        self.project_name = project_name
        self.message_buffer = []

        self.message_buffer.append(f"COMP310 AUTOGRADER REPORT FOR {project_name}")

        Reporter._reporters[project_name] = self

        Reporter._mailjet = smtplib.SMTP(host="in-v3.mailjet.com", port=587, timeout=5)
        Reporter._mailjet.login(user=os.environ["MJ_USERNAME"], password=os.environ["MJ_PASSWORD"])
        logging.info("Mailjet login successful")

        # with open(pathlib.Path(__file__).parent.parent / "resources/mapping.yml") as f:
        #     Reporter._mapping = yaml.safe_load(f)

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

        if os.getenv("DEBUG") == "1":
            print(full_message_body)
        else:
            send_email(self._emails, full_message_body)

        logging.debug(f"Sent report for {self.project_name}")
