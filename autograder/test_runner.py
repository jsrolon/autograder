import subprocess
import pathlib

from . import reporter


class TestRunner:
    rep: reporter.Reporter
    project_location: pathlib.Path

    def __init__(self, project_identifier: str, project_location: pathlib.Path):
        self.rep = reporter.get_reporter(project_identifier)
        self.project_location = project_location

    def run_test(self, test: str):
        completed_process = subprocess.run(f"mysh < {test}.txt",
                                           shell=True, capture_output=True, timeout=30, encoding='UTF-8')
        if completed_process.returncode == 0:
            with open(pathlib.Path(self.project_location, "testcases", f"{test}_result.txt"), 'r') as expected_output:
                if completed_process.stdout == expected_output:
                    self.rep.succeed(test)
        else:
            self.rep.fail(test)

    def run_all(self):
        test_input_files = self.project_location.glob("/testcases/*.txt")
        test_names = []
        for test_input_file in test_input_files:
            test_names.append(test_input_file.stem)

        for test in test_names:
            self.run_test(test)
