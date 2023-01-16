import subprocess
import pathlib

from autograder.project.reporter import Reporter


def jaccard(actual: str, expected: str) -> float:
    actual_set = set(actual.split())
    expected_set = set(expected.split())
    intersection = actual_set.intersection(expected_set)
    union = actual_set.union(expected_set)
    return float(len(intersection) / len(union))


class TestRunner:
    rep: Reporter
    project_path: pathlib.Path

    def __init__(self, project_identifier: str, project_location: pathlib.Path):
        self.rep = Reporter.get_reporter(project_identifier)
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

        timed_out = False
        try:
            # clean and recompile
            subprocess.check_call(["make", "clean"], cwd=binary_path)
            subprocess.check_call(["make"], cwd=binary_path)

            # actually run the test
            completed_process = subprocess.run(f"./mysh < {test_input_path}",
                                               shell=True,
                                               capture_output=True,
                                               timeout=1,
                                               encoding='UTF-8',
                                               cwd=binary_path)
            output = completed_process.stdout
        except subprocess.TimeoutExpired as e:
            output = e.output.decode('utf-8')
            timed_out = True

        expected_output_path = pathlib.Path(assignment_path, f"{test}_result.txt")
        with open(expected_output_path, 'r') as expected_output:
            expected_output_str = expected_output.read()
            jac = jaccard(output, expected_output_str)
            # todo: add strace verifications?
            if jac > 0.95:
                self.rep.succeed(test)
                return

        if timed_out:
            self.rep.timeout(test)
            return

        self.rep.fail(test)
