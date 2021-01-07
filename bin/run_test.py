#!/usr/bin/env python3
#      This file is part of quicky_tools
#      Copyright (C) 2020  Julien Thevenon ( julien_thevenon at yahoo.fr )
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU General Public License as published by
#      the Free Software Foundation, either version 3 of the License, or
#      (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU General Public License for more details.
#
#      You should have received a copy of the GNU General Public License
#      along with this program.  If not, see <http://www.gnu.org/licenses/>
import shlex
import shutil
import subprocess
import sys
import os
import glob
from os import path


class TestInfo:
    def __init__(self):
        self._args = ""
        self._exe = ""
        self._expected_status = 0
        self._timeout = 5
        self._reference_files = []
        self._expected_stdout_strings = []

    def set_arg(self, arg):
        self._args = arg

    def get_arg(self):
        return self._args

    def set_exe(self, exe):
        self._exe = exe

    def get_exe(self):
        return self._exe

    def set_expected_status(self, status):
        self._expected_status = int(status)

    def get_expected_status(self):
        return self._expected_status

    def set_timeout(self, timeout):
        self._timeout = int(timeout)

    def get_timeout(self):
        return self._timeout

    def add_reference_file(self, file):
        self._reference_files.append(file)

    def get_reference_files(self):
        return self._reference_files

    def add_expected_stdout_string(self, string):
        self._expected_stdout_strings.append(string)

    def get_expected_stdout_strings(self):
        return self._expected_stdout_strings


def extract_test_info(test_path):
    info_file_name = path.join(test_path, "test.info")
    if not path.exists(info_file_name):
        print("ERROR : Missing test.info for test in " + test_path)
        return [-1, 0]

    print("--> Parse file " + info_file_name)

    test_info = TestInfo()

    with open(info_file_name, "r") as info_file:
        line_number = 1
        for line in info_file:
            line = line.rstrip()
            # Ignore comments
            if line.startswith("#"):
                continue

            # Extract key values
            if -1 != line.find(":"):
                (key, value) = line.split(":", maxsplit=1)
                if "exe_file" == key:
                    test_info.set_exe(value)
                elif "args" == key:
                    while -1 != value.find("<test_location>"):
                        value = value.replace("<test_location>", test_path)
                    test_info.set_arg(value)
                elif "expected_stdout_string" == key:
                    test_info.add_expected_stdout_string(value)
                elif "expected_status" == key:
                    test_info.set_expected_status(value)
                else:
                    print("ERROR: Unknown key " + key + ' in line "' + line + '" ', end='')
                    print("at " + path.basename(info_file_name) + ":" + str(line_number))
                    return [-1, 0]
            else:
                print('ERROR: No key/value syntax in line "' + line, end='')
                print('" at ' + path.basename(info_file_name) + ":" + str(line_number))
                return [-1, 0]

            line_number += 1
    if "" == test_info.get_exe():
        print('ERROR: Exe file not defined')
        return [-1, 0]
    return [0, test_info]


def perform_test(name, test_path, compilation_path):
    print('-> Prepare test "' + name + '"')

    (status, test_info) = extract_test_info(test_path)

    # Check if extraction of test information was OK
    if 0 != status:
        return status

    # Find executable file ( different naming between quicky tools and CMake
    binary_candidates = (path.join(compilation_path, test_info.get_exe()),
                         path.join(compilation_path, "bin", test_info.get_exe() + ".exe"))
    exe_name = ""
    for binary_candidate in binary_candidates:
        if path.exists(binary_candidate):
            exe_name = binary_candidate

    if "" == exe_name:
        print("ERROR : Unable to find exe " + test_info.get_exe() + " in " + compilation_path)
        return -1

    # Build the command
    test_cmd = [exe_name]
    test_cmd += shlex.split(test_info.get_arg())

    # Log the command
    with open("cmd.log", "w") as cmd_file:
        cmd_file.write(' '.join(test_cmd))

    # Launch process
    print('-> Run test "' + name + '"')
    process = subprocess.Popen(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdouts, stderrs = process.communicate(timeout=test_info.get_timeout())
    except subprocess.TimeoutExpired:
        process.kill()
        stdouts, stderrs = process.communicate()

    # Compare expected status vs status
    if process.returncode != test_info.get_expected_status():
        print("ERROR: return status(" + str(process.returncode) + ") different from expected one(", end='')
        print(str(test_info.get_expected_status()) + ")")
        status = -1

    # Dump logs for stdout, stderr, return status
    with open("stdout.log", "w") as stdout_log:
        stdout_log.write(str(stdouts, 'utf-8'))
    with open("stderr.log", "w") as stderr_log:
        stderr_log.write(str(stderrs, 'utf-8'))
    with open("status.log", "w") as status_log:
        status_log.write(str(process.returncode))

    # Check reference files
    root_reference = path.join(test_path, "references")
    for abs_reference_file in glob.iglob(path.join(root_reference, "**"), recursive=True):
        if path.isdir(abs_reference_file) or not path.exists(abs_reference_file):
            continue
        relative_file = path.basename(abs_reference_file)
        reference_file = path.dirname(abs_reference_file)
        while reference_file != root_reference:
            relative_file = path.join(path.basename(reference_file), relative_file)
            reference_file = path.dirname(reference_file)
        if path.exists(relative_file):
            print("--> Compare " + relative_file + " with reference")
            with subprocess.Popen(["diff", relative_file, abs_reference_file],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE) as diff_process:
                diff_process.wait()
                if 0 != diff_process.returncode:
                    print("ERROR: " + ' '.join(diff_process.args))
                    status = diff_process.returncode
        else:
            print('ERROR: file "' + relative_file + '" expected but not created')
            status = -1

    # Search for expected strings
    stdout_content = str(stdouts, 'utf-8').split('\n')
    expected_strings = test_info.get_expected_stdout_strings()
    for line in stdout_content:
        if len(expected_strings):
            if line == expected_strings[0]:
                expected_strings.pop(0)
        else:
            break

    for expected_stdout_string in expected_strings:
        print('ERROR: expected string "' + expected_stdout_string + '" is missing in stdout ', end='')
        print('or was not at the expected place')
        status = -1

    return status


def main(argv):
    if 1 != len(argv):
        print("ERROR : need to have 1 argument")
        sys.exit(-1)

    assert ("PWD" in os.environ)
    compilation_path = os.environ["PWD"]
    print("Compilation path : " + compilation_path)

    # Get test root location
    test_root = argv[0]
    print("Run tests located in " + test_root)

    if not path.isabs(test_root):
        test_root = path.join(compilation_path, test_root)

    # Check test location existence
    if not path.exists(test_root):
        print("ERROR : directory " + test_root + " do not exists")
        sys.exit(-1)

    if not path.isdir(test_root):
        print("ERROR : " + test_root + " is not a directory")
        sys.exit(-1)

    # Create file tree for test execution
    execution_path = path.join(compilation_path, "test_results")
    print("Execution path : " + execution_path)
    if not path.exists(execution_path):
        os.mkdir(execution_path)

    test_status = 0
    # Iterate over tests
    for item in os.scandir(test_root):
        if item.is_dir():
            test_location = path.join(test_root, item.name)
            test_execution_path = path.join(execution_path, item.name)

            # Remove test execution directory if it already exist
            if path.exists(test_execution_path):
                shutil.rmtree(test_execution_path)

            # Create test execution directory
            os.mkdir(test_execution_path)

            # Go in specific test execution directory
            os.chdir(test_execution_path)

            test_status += perform_test(item.name, test_location, compilation_path)

            # Come back to execution directory after the test
            os.chdir(execution_path)

    if 0 == test_status:
        print("TESTS SUCCESSFUL")
    else:
        print("TESTS FAILED")
    sys.exit(test_status)


if __name__ == "__main__":
    # execute only if run as a script
    main(sys.argv[1:])
# EOF
