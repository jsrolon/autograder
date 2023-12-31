import base64
import csv
import logging
import os
import threading

from mailjet_rest import Client

from autograder import cfg

mailjet = Client(
    auth=(cfg.MJ_USERNAME, cfg.MJ_PASSWORD),
    version='v3.1')

csv_lock = threading.Lock()
csv_writer = csv.writer(cfg.AUTOGRADER_CSV_REPORT_FILE)


def write_csv_line(team_id, test_name, result):
    with csv_lock:
        csv_writer.writerow([team_id, test_name, result])


def mj_send_email(to, body, id, attachments):
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
                "Attachments": attachments
            }
        ],
        'SandboxMode': sandbox
    }
    try:
        result = mailjet.send.create(data=data)
        if result.status_code == 200:
            logging.info(f"(SANDBOX {sandbox}) Sent email to {id} members {to}")
        else:
            logging.error(f"Email sending to {id} members {to} failed with status {result.status_code}")
    except:
        logging.error(f"Exception sending email for {id}")


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

    _output_attachments = {}

    @staticmethod
    def get_reporter(project_identifier: str):
        return Reporter._reporters[project_identifier]

    def __init__(self, project_name: str):
        # self._emails = emails

        self.project_name = project_name
        project_unique_id = project_name.split('/')[0]

        self.message_buffer = []

        self.per_test_buffer = []

        self.current_buffer = self.message_buffer

        self.message_buffer.append(f"COMP310 AUTOGRADER REPORT FOR {project_name}")

        self.test_outputs_folder = cfg.AUTOGRADER_TEST_OUTPUTS_PATH / project_unique_id
        self.can_write_outputs = False
        try:
            self.test_outputs_folder.mkdir(parents=True, exist_ok=True)
            self.can_write_outputs = True
        except:
            logging.warning(f"Could not create test output folder for {project_unique_id}")

        Reporter._reporters[project_name] = self

    def append(self, message: str):
        self.current_buffer.append(message)

    def append_same_line(self, message: str):
        if len(self.current_buffer) > 0:
            last_str = self.current_buffer[-1]
            new_str = f"{last_str} {message}"
            self.current_buffer[-1] = new_str
        else:
            self.append(message)

    def succeed(self, test_name: str):
        self.current_buffer.append(f"# {test_name:<25} {self.PASS}")
        write_csv_line(self.project_name, test_name, "PASS")

    def fail(self, test_name: str):
        self.current_buffer.append(f"# {test_name:<25} {self.FAIL}")
        write_csv_line(self.project_name, test_name, "FAIL")

    def timeout(self, test_name: str):
        self.current_buffer.append(f"# {test_name:<25} {self.TIMEOUT}")
        write_csv_line(self.project_name, test_name, "TIMEOUT")

    def exit_code(self, test_name: str, exit_code: int):
        if exit_code in RETURN_CODES:
            self.current_buffer.append(f"# {test_name:<25} {RETURN_CODES[exit_code]}")
        else:
            self.current_buffer.append(f"# {test_name:<25} Abnormal exit code {exit_code}")

    def enable_per_test_buffer(self):
        self.per_test_buffer = []
        self.current_buffer = self.per_test_buffer

    def flush_per_test_buffer(self):
        self.message_buffer.extend(self.per_test_buffer)
        self.current_buffer = self.message_buffer

    def add_output(self, test_name: str, test_output: str):
        self._output_attachments[test_name] = {
            "ContentType": "text/plain",
            "Filename": f"{test_name}_output.txt",
            "Base64Content": base64.b64encode(bytes(test_output, 'utf-8')).decode('utf-8')
        }

        if self.can_write_outputs:
            with open(self.test_outputs_folder / f"{test_name}_output.txt", 'w') as f:
                f.write(test_output)

    def send_email(self):
        full_message_body = "\n".join(self.message_buffer)
        if cfg.DEBUG:
            print(full_message_body)

        if self.project_name in cfg.FORKS:
            mj_send_email(cfg.FORKS[self.project_name], full_message_body, self.project_name, list(self._output_attachments.values()))
            cfg.AUTOGRADER_REPORT_PATH.mkdir(parents=True, exist_ok=True)
            with open(f"{cfg.AUTOGRADER_WORKING_DIR}/reports/{self.project_name.split('/')[0]}.txt", 'w') as f:
                f.write(full_message_body)
                f.close()
        else:
            logging.error(f"No emails found for {self.project_name}")
