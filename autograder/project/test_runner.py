import logging
import re
import subprocess
import pathlib
import os
import signal
import difflib

from autograder import cfg
from autograder.project.reporter import Reporter


def ordered(actual: str, expected: str) -> float:
    actual_lines = actual.split()
    expected_lines = expected.split()
    ratio = difflib.SequenceMatcher(isjunk=None, a=expected_lines, b=actual_lines, autojunk=False).ratio()
    return ratio


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
        for assignment_path in assignments:
            assignment_name = assignment_path.stem
            self.rep.append(assignment_name)

            test_result_files = assignment_path.glob("*_result.txt")
            test_names = map(lambda f: f.stem.replace("_result", ""), test_result_files)
            num_tests = 0
            num_passed = 0
            for test in test_names:
                num_tests += 1

                order_matters = False
                if assignment_name in cfg.ORDER_MATTERS:
                    order_matters = test in cfg.ORDER_MATTERS[assignment_name]

                run_multiple = False
                if assignment_name in cfg.RUN_MULTIPLE:
                    run_multiple = test in cfg.RUN_MULTIPLE[assignment_name]

                passed = False
                if run_multiple:
                    iterations = cfg.AUTOGRADER_MT_ITERATIONS
                    i = 1
                    while i <= iterations:
                        self.rep.enable_per_test_buffer()  # need to reset the temp buffer on every run
                        passed = self.run_test(test, assignment_path, order_matters)
                        if not passed:
                            break
                        i += 1

                    if not passed:
                        self.rep.append_same_line(f"on run {i} out of {iterations}")

                    self.rep.flush_per_test_buffer()
                else:
                    passed = self.run_test(test, assignment_path, order_matters)

                if passed:
                    num_passed += 1

            self.rep.append(f"Passed {num_passed} / {num_tests}")
            self.rep.append(f"{assignment_name} score {num_passed/num_tests:.0%}\n")

    def run_test(self, test: str, assignment_path: pathlib.Path, order_matters: bool):
        binary_path = pathlib.Path(self.project_path, "src")
        test_input_path = pathlib.Path(assignment_path, f"{test}.txt")

        a3_frame_store_sz = 18
        a3_var_store_sz = 10
        if assignment_path.stem == "assignment3":
            expected_output_path = pathlib.Path(assignment_path, f"{test}_result.txt")
            with open(expected_output_path, 'r') as expected_output:
                expected_output_str = expected_output.read()
                mem_sizes = re.findall(r'(?<=Size = )(\d+)', expected_output_str)
                if len(mem_sizes) == 2:
                    a3_frame_store_sz, a3_var_store_sz = mem_sizes
                    logging.debug(f"parsed framestore={a3_frame_store_sz} varstore={a3_var_store_sz}")

        timed_out = False
        try:
            completed_make_clean = subprocess.run(["make", "clean"],
                                                  timeout=15, cwd=binary_path, capture_output=cfg.CAPTURE_OUTPUT)
            if completed_make_clean.returncode != 0:
                self.rep.append(f"# {test:<25} 'make clean' failed (return code {completed_make_clean.returncode})")
                return False
        except Exception as e:
            self.rep.append(f"# {test:<25} 'make clean' failed ({e.__class__.__name__})")
            return False

        try:
            completed_make = subprocess.run(cfg.autograder_make_command_line(a3_frame_store_sz, a3_var_store_sz),
                                            timeout=15, cwd=binary_path, capture_output=cfg.CAPTURE_OUTPUT)

            if completed_make.returncode != 0:
                self.rep.append(f"# {test:<25} 'make' failed (return code {completed_make.returncode})")
                return False
        except Exception as e:
            self.rep.append(f"# {test:<25} 'make' failed ({e.__class__.__name__})")
            return False

        # actually run the test
        bubblewrap_string = ""
        # if shutil.which("bwrap"):
        #     bubblewrap_string = f"bwrap --unshare-all --ro-bind / / --dev-bind {binary_path} {binary_path} "
        process = subprocess.Popen(f"{bubblewrap_string}{binary_path}/mysh < {test_input_path}",
                                   shell=True,
                                   cwd=assignment_path,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   start_new_session=True)  # crucial to ensure spawned processes die
        # https://alexandra-zaharia.github.io/posts/kill-subprocess-and-its-children-on-timeout-python/

        try:
            process.wait(timeout=15)
            output = process.stdout
            if process.returncode != 0:
                self.rep.exit_code(test, process.returncode)
                return False
        except subprocess.TimeoutExpired as e:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            timed_out = True
            if e.output:
                output = e.output
            else:
                self.rep.timeout(test)
                return False

        # handling weird unicode error thing
        if output:
            try:
                output = output.read().decode('utf-8')
                self.rep.add_output(test, output)
                if cfg.DEBUG:
                    output_file_path = f"{cfg.AUTOGRADER_WORKING_DIR}/{self.rep.project_name.split('/')[0]}_{assignment_path.stem}_{test}.txt"
                    with open(output_file_path, 'w') as f:
                        f.writelines(output)
            except UnicodeError:
                logging.info(f"For {self.project_path} error decoding output on {test}")
                self.rep.fail(test)
                return False

        # comparing outputs
        possible_results = assignment_path.glob(f"{test}_result*.txt")
        for possible_result in possible_results:
            with open(possible_result, 'r') as expected_output:
                expected_output_str = expected_output.read()
                if order_matters:
                    score = ordered(output, expected_output_str)
                else:
                    score = jaccard(output, expected_output_str)

                if score >= 0.9:
                    self.rep.succeed(test)
                    return True

        if timed_out:
            self.rep.timeout(test)
            return False

        self.rep.fail(test)
        return False
