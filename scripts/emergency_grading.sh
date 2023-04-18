#!/usr/bin/env bash

repos_folder="${1:-$HOME/repos}"

src_folder_path="src"
testcases_path="testcases/assignment3"

binary_name="mysh"
original_binary_path="${src_folder_path}/${binary_name}"
testcases_binary_path="${testcases_path}/${binary_name}"

for repo in ${repos_folder}/**/**; do
  if [[ "${repo}" =~ .*balmau.* ]]; then
    true
  else
    # get into students' repo
    pushd "${repo}" || exit

    echo "EMERGENCY AUTOGRADER REPORT FOR ${repo}"
    echo "As of commit $(git rev-parse HEAD)"

    # get into the src folder to compile
    pushd "${src_folder_path}" || exit
    make --silent clean
    make --silent
    popd || exit

    cp "${original_binary_path}" "${testcases_binary_path}"

    pushd "${testcases_path}" || exit
    for test_result_name in *_result.txt; do
      test_name="${test_result_name//_result/}" # remove the "_result" substring
      actual_output_name="${test_name//.txt/}_actual.txt"
      ${testcases_binary_path} < "${test_name}" > "${actual_output_name}"
      if diff --ignore-all-space "${test_result_name}" "${actual_output_name}"; then
        echo "${test_name} PASS"
      else
        echo "${test_name} FAIL"
      fi
    done

    # exit students' folder
    popd || exit
  fi
done
