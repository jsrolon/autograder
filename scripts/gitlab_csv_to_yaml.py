#!/usr/bin/env python3

import csv
import sys

import yaml
import re
from pathlib import Path

if len(sys.argv) != 2:
    print(f"Error: Need path to CSV file")
    sys.exit(1)

path_to_csv = sys.argv[1]

fork_regex = re.compile(r'^.+gitlab\.cs\.mcgill\.ca[:\/]([A-z0-9-]+)\/([A-z0-9-]+)')
output_dict = {}

with open(path_to_csv, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        fork_url_as_is = row["GitHub Fork URL"]
        fork_url_match = fork_regex.match(fork_url_as_is)
        if fork_url_match:
            (gitlab_group, gitlab_project) = fork_url_match.groups()
            project_path = f"{gitlab_group}/{gitlab_project}"
            if project_path not in output_dict:
                output_dict[project_path] = []

            output_dict[project_path].append(row["Email"])
        else:
            print(f"{fork_url_as_is} doesnt match expected pattern")

output_path = Path(__file__).parent / "../autograder/resources/mapping.yaml"
with open(output_path, "w") as out:
    yaml.dump(output_dict, out)
