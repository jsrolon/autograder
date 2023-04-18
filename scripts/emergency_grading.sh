#!/usr/bin/env bash

#set -x

repos_folder="/data/repos"

src_folder_path="src"
professor_path="${repos_folder}/balmau/comp310-winter23"
testcases_path="${professor_path}/testcases/assignment3"

binary_name="mysh"
original_binary_path="${src_folder_path}/${binary_name}"
testcases_binary_path="${testcases_path}/${binary_name}"

a3_reports_folder="/data/a3_reports"
rm -rf "${a3_reports_folder}"
mkdir -p "${a3_reports_folder}"

#for repo in "${repos_folder}/fsinti/comp310project"; do
for repo in ${repos_folder}/**/**; do
  if [[ "${repo}" =~ .*balmau.* ]]; then
    true
  else
    repo_identifier="$(basename $(dirname ${repo}))"
    log_path="${a3_reports_folder}/${repo_identifier}.txt"
    echo "Gonna run ${repo_identifier}"

    pushd "${repo}" > /dev/null || exit # get into students' repo

    echo "EMERGENCY AUTOGRADER REPORT FOR ${repo_identifier}" >> "${log_path}"
    echo "As of commit $(git rev-parse HEAD)" >> "${log_path}"

    passed=0
    for test_result_path in ${testcases_path}/*_result.txt; do
      test_path="${test_result_path//_result/}" # remove the "_result" substring
      test_name="$(basename ${test_path})"
      actual_output_path="${test_name//.txt/}_actual.txt"

      # obtain compilation parameters
      frame_store_size=$(grep --perl-regexp --only-matching "(?<=Frame Store Size = )\d+" "${test_result_path}")
      var_store_size=$(grep --perl-regexp --only-matching "(?<=Variable Store Size = )\d+" "${test_result_path}")

      if [[ ! -d "${src_folder_path}" ]]; then
          echo "Repo structure not found" >> "${log_path}"
	        continue
      fi  

      # ensure everything is clean in the working directory
      git -C "${professor_path}" clean -d --force

      # compile
      pushd "${src_folder_path}" > /dev/null || exit # get into src for make
      make clean &> /dev/null
      if make CC=gcc-11 framesize="${frame_store_size}" varmemsize="${var_store_size}" &> /dev/null; then
        popd > /dev/null || exit # return to student's repo

        pushd "${testcases_path}" > /dev/null || exit # move to prof's assignment3 repo
        timeout 5 ${repo}/${original_binary_path} < "${test_path}" > "${actual_output_path}"

        if diff --ignore-all-space "${test_result_path}" "${actual_output_path}" &> /dev/null; then
          echo "${test_name} PASS" >> "${log_path}"
          passed=$((passed+1))
        else
          echo "${test_name} FAIL" >> "${log_path}"
        fi

	      popd > /dev/null || exit # return to student's repo
        #rm -f "${testcases_binary_path}"
      else
        popd > /dev/null || exit # return to student's repo
        echo "${test_name} Compilation FAIL" >> "${log_path}"
      fi
    done

    echo "Score ${passed}/10" >> "${log_path}"; echo; echo

    popd > /dev/null || exit # exit students' repo
  fi
done
