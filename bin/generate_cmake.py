#!/usr/bin/python3
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

import sys
import glob
import os
from os import path


def main(argv):
    if 1 != len(argv):
        print("ERROR : need to have 1 argument")
        sys.exit(-1)

    project_name = argv[0]
    print("Generate CMake file for " + project_name)

    # Get quicky_tools location
    location = ""
    if "QUICKY_TOOLS" in os.environ:
        location = os.environ["QUICKY_TOOLS"]
    else:
        print("ERROR: QUICKY_TOOLS env variable not set")
        sys.exit(-1)

    # Create dictionnary from infra file
    if not path.exists("infra_infos.txt"):
        print("ERROR : infra_infos.txt not found")
        sys.exit(-1)

    infra_infos = {}
    infra_file = open("infra_infos.txt", "r")
    for line in infra_file:
        column_position = line.find(":")
        if -1 != column_position:
            key = line[0:column_position]
            value = line[1 + column_position:].rstrip()
            infra_infos[key] = value

    # Get list of source files
    source_files = list()
    source_files = source_files + ([file for file in glob.glob("include/*") if -1 == file.find("~")])
    source_files = source_files + ([file for file in glob.glob("src/*") if -1 == file.find("~") and not file.endswith("main_" + project_name + ".cpp")])

    # Use generic reference file to generate CMakeLists file by replacing  some
    # special strings by project information
    reference_file = open(location + "/data/CMakeLists.txt.ref", "r")
    output_file = open("CMakeLists.txt", "w")
    for line in reference_file:
        # Manage project name
        if -1 != line.find("<to_be_defined>"):
            output_file.write(line.replace("<to_be_defined>", project_name))
        elif -1 != line.find("<source_files>"):
            for file in source_files:
                source_line = line.replace("<source_files>", file)
                output_file.write(source_line)
        elif -1 != line.find("<dependancies>"):
            for dependancy in infra_infos["depend"].split():
                dependancy_line = line.replace("<dependancies>", '"' + dependancy + '"')
                output_file.write(dependancy_line)
        else:
            output_file.write(line)
    reference_file.close()
    output_file.close()


if __name__ == "__main__":
    # execute only if run as a script
    main(sys.argv[1:])
# EOF
