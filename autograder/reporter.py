
PASS = "PASS"
FAIL = "FAIL"

registered_reporters = {}


def get_reporter(name: str):
    return registered_reporters[name]


class Reporter:
    def __init__(self, project_name: str):
        registered_reporters[project_name] = self

        self.project_name = project_name
        self.message_buffer = []

        self.message_buffer.append(f"AUTOGRADER REPORT FOR {project_name}")

    def append(self, message: str):
        self.message_buffer.append(message)

    def succeed(self, test_name: str):
        self.message_buffer.append(f"# {test_name}\t\t{PASS}")

    def fail(self, test_name: str):
        self.message_buffer.append(f"# {test_name}\t\t{FAIL}")

    def send(self):
        full_message = "\n".join(self.message_buffer)
        print(full_message)
