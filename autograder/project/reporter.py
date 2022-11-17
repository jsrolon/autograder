import logging
import smtplib
import os
from email.message import EmailMessage
import pathlib

import yaml


# this should execute only once
_mailjet = smtplib.SMTP(host="in-v3.mailjet.com", port=587, timeout=5)
_mailjet.login(user=os.environ["MJ_USERNAME"], password=os.environ["MJ_PASSWORD"])

with open(pathlib.Path(__file__).parent.parent / "resources/mapping.yml") as f:
    _mapping = yaml.safe_load(f)


class Reporter:
    PASS = "PASS"
    FAIL = "FAIL"
    TIMEOUT = "TIMEOUT"

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.message_buffer = []

        self.message_buffer.append(f"COMP310 AUTOGRADER REPORT FOR {project_name}")

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
            msg = EmailMessage()
            msg["Subject"] = "COMP310 Autograder Report"
            msg["From"] = os.getenv("AUTOGRADER_EMAIL_FROM_ADDR", default="sebastian.rolon@mcgill.ca")
            try:
                msg["To"] = _mapping[self.project_name]
            except KeyError:
                logging.error(f"Email add")
            msg.set_content(full_message_body)

            _mailjet.send_message(msg)

        logging.debug(f"Sent report for {self.project_name}")
