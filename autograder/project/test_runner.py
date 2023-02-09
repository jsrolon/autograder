import logging
import shutil
import subprocess
import pathlib
import os
import signal

from autograder import cfg
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

        assignments = cfg.AUTOGRADER_BASE_REPO_CLONE_PATH.glob("testcases/*")
        for assignment in assignments:
            self.rep.append(assignment.stem)
            test_result_files = assignment.glob("*_result.txt")
            test_names = map(lambda f: f.stem.replace("_result", ""), test_result_files)
            for test in test_names:
                self.run_test(test, assignment)

    def run_test(self, test: str, assignment_path: pathlib.Path):
        binary_path = pathlib.Path(self.project_path, "src")
        test_input_path = pathlib.Path(assignment_path, f"{test}.txt")

        timed_out = False
        try:
            # clean and recompile
            completed_make_clean = subprocess.run(["make", "clean"],
                                                  timeout=1, cwd=binary_path, capture_output=cfg.CAPTURE_OUTPUT)
            completed_make = subprocess.run(["make", "CC=gcc-11"],
                                            timeout=1, cwd=binary_path, capture_output=cfg.CAPTURE_OUTPUT)

            if completed_make_clean.returncode != 0 or completed_make.returncode != 0:
                logging.info(f"Unexpected make failed on {test} for {self.project_path}")
                self.rep.fail(test)
                return

            # actually run the test
            bubblewrap_string = ""
            if shutil.which("bwrap"):
                bubblewrap_string = f"bwrap --unshare-all --ro-bind / / --dev-bind {binary_path} {binary_path} "
            process = subprocess.Popen(f"{bubblewrap_string}{binary_path}/mysh < {test_input_path}",
                                       shell=True,
                                       cwd=binary_path,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       start_new_session=True)  # crucial to ensure spawned processes die
            # https://alexandra-zaharia.github.io/posts/kill-subprocess-and-its-children-on-timeout-python/

            process.wait(timeout=1)
            output = process.stdout
            if process.returncode != 0:
                self.rep.exit_code(test, process.returncode)
                return
        except subprocess.TimeoutExpired as e:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            timed_out = True
            if e.output:
                output = e.output
            else:
                self.rep.timeout(test)
                return

        # handling weird unicode error thing
        if output:
            try:
                output = output.read().decode('utf-8')
            except UnicodeError as e:
                logging.info(f"For {self.project_path} error decoding output on {test}")
                self.rep.fail(test)
                return

        # comparing outputs
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
