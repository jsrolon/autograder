import logging
import smtplib
import os
from email.message import EmailMessage

PASS = "PASS"
FAIL = "FAIL"
TIMEOUT = "TIMEOUT"

registered_reporters = {}


def get_reporter(name: str):
    return registered_reporters[name]


class Reporter:
    def __init__(self, project_name: str):
        registered_reporters[project_name] = self

        self.project_name = project_name
        self.message_buffer = []

        self.message_buffer.append(f"COMP310 AUTOGRADER REPORT FOR {project_name}")

    def append(self, message: str):
        self.message_buffer.append(message)

    def succeed(self, test_name: str):
        self.message_buffer.append(f"# {test_name:<25} {PASS}")

    def fail(self, test_name: str):
        self.message_buffer.append(f"# {test_name:<25} {FAIL}")

    def timeout(self, test_name: str):
        self.message_buffer.append(f"# {test_name:<25} {TIMEOUT}")

    def send(self):
        full_message_body = "\n".join(self.message_buffer)

        msg = EmailMessage()
        msg["Subject"] = "COMP310 Autograder Report"
        msg["From"] = "sebastian.rolon@mcgill.ca"
        msg["To"] = "sebastian.rolon@mail.mcgill.ca"
        msg.set_content(full_message_body)

        mailjet = smtplib.SMTP(host="in-v3.mailjet.com", port=587, timeout=5)
        mailjet.login(user=os.environ["MJ_USERNAME"], password=os.environ["MJ_PASSWORD"])
        mailjet.send_message(msg)

        logging.debug(f"Sent report for {self.project_name}")
