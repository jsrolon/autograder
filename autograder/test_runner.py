import subprocess
import pathlib

from . import reporter


class TestRunner:
    rep: reporter.Reporter
    project_path: pathlib.Path

    def __init__(self, project_identifier: str, project_location: pathlib.Path):
        self.rep = reporter.get_reporter(project_identifier)
        self.project_path = project_location

    def run_all(self):
        self.rep.append("\nTEST CASES")

        assignments = self.project_path.glob("testcases/*")
        for assignment in assignments:
            self.rep.append(assignment.stem)
            test_result_files = assignment.glob("*_result.txt")
            test_names = map(lambda f: f.stem.split("_")[0], test_result_files)
            for test in test_names:
                self.run_test(test, assignment)

    def run_test(self, test: str, assignment_path: pathlib.Path):
        binary_path = pathlib.Path(self.project_path, "src")
        test_input_path = pathlib.Path(assignment_path, f"{test}.txt")
        try:
            completed_process = subprocess.run(f"./mysh < {test_input_path}",
                                               shell=True,
                                               capture_output=True,
                                               timeout=1,
                                               encoding='UTF-8',
                                               cwd=binary_path)
            if completed_process.returncode == 0:
                expected_output_path = pathlib.Path(assignment_path, f"{test}_result.txt")
                with open(expected_output_path, 'r') as expected_output:
                    if completed_process.stdout == expected_output.read():
                        self.rep.succeed(test)

            self.rep.fail(test)
        except subprocess.TimeoutExpired:
            self.rep.timeout(test)
