#!/usr/bin/env bash

#set -x

repos_folder="${1:-$HOME/repos}"

src_folder_path="src"
testcases_path="${repos_folder}/balmau/comp310-winter23/testcases/assignment3"

binary_name="mysh"
original_binary_path="${src_folder_path}/${binary_name}"
testcases_binary_path="${testcases_path}/${binary_name}"

for repo in "${repos_folder}/jchen213/comp-310-winter-23-solution"; do
#for repo in ${repos_folder}/**/**; do
  if [[ "${repo}" =~ .*balmau.* ]]; then
    true
  else
    # get into students' repo
    pushd "${repo}" > /dev/null || exit

    echo "EMERGENCY AUTOGRADER REPORT FOR ${repo}"
    echo "As of commit $(git rev-parse HEAD)"

    passed=0
    for test_result_path in ${testcases_path}/*_result.txt; do
      test_result_name=$(basename "${test_result_path}") # get only the filename
      test_path="${test_result_path//_result/}" # remove the "_result" substring
      test_name="$(basename ${test_path})"
      actual_output_path="${test_name//.txt/}_actual.txt"

      # obtain compilation parameters
      frame_store_size=$(grep --perl-regexp --only-matching "(?<=Frame Store Size = )\d+" "${test_result_path}")
      var_store_size=$(grep --perl-regexp --only-matching "(?<=Variable Store Size = )\d+" "${test_result_path}")

      # compile
      pushd "${src_folder_path}" > /dev/null || exit
      make clean &> /dev/null
      if make CC=gcc-11 framesize="${frame_store_size}" varmemsize="${var_store_size}" &> /dev/null; then
        popd > /dev/null || exit

        cp -f "${original_binary_path}" "${testcases_binary_path}"

        ${testcases_binary_path} < "${test_path}" > "${actual_output_path}"

        if diff --ignore-all-space "${test_result_path}" "${actual_output_path}" &> /dev/null; then
          echo "${test_name} PASS"
          passed=$((passed+1))
        else
          echo "${test_name} FAIL"
        fi

        rm -f "${testcases_binary_path}"
      else
        popd > /dev/null || exit
        echo "${test_name} Compilation FAIL"
      fi
    done

    echo "Score ${passed}/10"
    sleep 10

    # exit students' folder
    popd > /dev/null || exit
  fi
done
