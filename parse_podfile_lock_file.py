#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import json
from collections import OrderedDict
import argparse

## The format of the Podfile.lock
# PODS:
# ...
# DEPENDENCIES:
# ...
# SPEC REPOS:
# ...
# EXTERNAL SOURCES:
# ...
# SPEC CHECKSUMS:
# ...
# PODFILE CHECKSUM: ...
# COCOAPODS: ...
# 

# Note: different version of cocoapods, the format of the Podfile.lock is slightly different

## Podfile.lock keywords
PODS='PODS'
DEPENDENCIES='DEPENDENCIES'
COCOAPODS='COCOAPODS'
SPEC_CHECKSUMS='SPEC CHECKSUMS'
PODFILE_CHECKSUM='PODFILE CHECKSUM'
EXTERNAL_SOURCES='EXTERNAL SOURCES'
SPEC_REPOS='SPEC REPOS'
SEPARATOR=':'

## Custom keywords
POD_VERSIONS='POD_VERSIONS'

## Private keys
POD_INFO_NAME='pod_name'
POD_INFO_VERSION='pod_version'


def get_shared_logger():
    if 'sharedLogger' not in globals():
        logger = logging.getLogger('Podfile.lock parser')
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        if not logger.handlers:
            logger.addHandler(ch)

        globals()['sharedLogger'] = logger

    return globals()['sharedLogger']


def get_section_string(file_content, start_string, end_string):
    try:
        start_pos = file_content.index(start_string)
    except ValueError as e:
        return None
    start_index = start_pos + len(start_string)
    content = file_content[start_index:]

    try:
        end_pos = content.index(end_string)
    except ValueError as e:
        return None
    end_index = end_pos + len(end_string)
    section_string = content[:end_index]

    return section_string

def get_PODS_components(cocoapods_version, file_content):
    FISRT_LEVEL_PREFIX = '  - '
    SECOND_LEVEL_PREFIX = '    - '

    PODS_components_list = []

    PODS_string = get_section_string(file_content, f"{PODS}{SEPARATOR}", '\n\n')
    line_list = PODS_string.splitlines()
    index = 0
    while index < len(line_list):
        line = line_list[index]
        if line.strip() == '':
            index += 1
            continue

        if not line.startswith(FISRT_LEVEL_PREFIX):
            index += 1
            continue

        pod_name = line.strip(" -:").split(" ")[0]
        pod_version = line.strip(" -:").split(" ")[1].strip("()")

        pod_info_dict = {
            POD_INFO_NAME: pod_name,
            POD_INFO_VERSION: pod_version,
        }

        if line.endswith(":"):
            next_index = index + 1
            dependency_pod_list = []
            while next_index < len(line_list):
                next_line = line_list[next_index]
                if next_line.startswith(SECOND_LEVEL_PREFIX):
                    components = next_line.split("(")
                    assert len(components) == 1 or len(components) == 2, f"{components} must have one or tow elements"

                    dependency_pod_name = components[0].strip(" -")
                    if len(components) == 2:
                        dependency_pod_version = components[1].strip(")")
                        dependency_pod_info = {
                            POD_INFO_NAME: dependency_pod_name,
                            POD_INFO_VERSION: dependency_pod_version,
                        }
                    else:
                        dependency_pod_info = {
                            POD_INFO_NAME: dependency_pod_name,
                        }
                    dependency_pod_list.append(dependency_pod_info)
                    next_index += 1
                else:
                    break

            index = next_index
            if len(dependency_pod_list):
                pod_info_dict["pod_dependencies"] = dependency_pod_list
        else:
            index += 1
        PODS_components_list.append(pod_info_dict)

    return PODS_components_list


def get_DEPENDENCIES_components(cocoapods_version, file_content):
    LEVEL_PREFIX = '  - '

    DEPENDENCIES_string = get_section_string(file_content, f"{DEPENDENCIES}{SEPARATOR}", '\n\n')
    line_list = DEPENDENCIES_string.splitlines()

    dependency_list = []
    for line in line_list:
        if line.strip() == '':
            continue

        if not line.startswith(LEVEL_PREFIX):
            continue
        
        components = line.strip(" -").split('(')
        assert len(components) == 1 or len(components) == 2, f"{components} must only have one or two elements"
        pod_name = components[0].strip(' -')
        # Note: pod_version maybe from local source code, 
        # and maybe have words ["from", "tag", "branch", "commit"]

        if len(components) == 2:
            pod_version = components[1].strip(')')
            pod_info = {
                POD_INFO_NAME: pod_name,
                POD_INFO_VERSION: pod_version,
            }
        else:
            pod_info = {
                POD_INFO_NAME: pod_name,
            }
        dependency_list.append(pod_info)

    return dependency_list


def get_SPEC_CHECKSUMS_components(cocoapods_version, file_content):
    SPEC_CHECKSUMS_string = get_section_string(file_content, f"{SPEC_CHECKSUMS}{SEPARATOR}", '\n\n')
    line_list = SPEC_CHECKSUMS_string.splitlines()
    line_list = [x for x in line_list if x.strip()]

    podspec_checksum_list = []
    for x in line_list:
        components = x.split(':')
        assert len(components) == 2, f"{components} must only have two elements"
        checksum_info = {
            "pod_name": components[0].strip(),
            "checksum": components[1].strip(),
        }
        podspec_checksum_list.append(checksum_info)

    return podspec_checksum_list


def get_cocoapods_version(file_content):
    COCOAPODS_string = file_content[file_content.index(f"{COCOAPODS}") :]
    line_list = COCOAPODS_string.splitlines()
    line_list = [x for x in line_list if x.strip()]
    line_list = line_list[0].split(":")
    assert len(line_list) == 2, f"{line_list} must only have two elements"
    version = line_list[1].strip()

    return version

def get_pod_version_dict(PODS_components, DEPENDENCIES_components):
    missed_pod_list = []
    pod_version_dict = {}
    for x in PODS_components:
        pod_name = x[POD_INFO_NAME] if POD_INFO_NAME in x else None
        pod_version = x[POD_INFO_VERSION] if POD_INFO_VERSION in x else None
        if pod_name and pod_version:
            pod_version_dict[pod_name] = pod_version
        elif pod_name and pod_version is None:
            missed_pod_list.append(pod_name)

    if len(missed_pod_list) > 0:
        for x in DEPENDENCIES_components:
            pod_name = x[POD_INFO_NAME] if POD_INFO_NAME in x else None
            pod_version = x[POD_INFO_VERSION] if POD_INFO_VERSION in x else None
            if pod_name in missed_pod_list and pod_name and pod_version:
                pod_version_dict[pod_name] = pod_version
    
    return pod_version_dict


def run_podfile_lock_file_parser(podfile_lock_file_path, args):
    get_shared_logger().info("Podfile.lock file path: %s" % podfile_lock_file_path) if args.debug else None

    if not os.path.isfile(podfile_lock_file_path):
        get_shared_logger().error("%s is not exist!" % podfile_lock_file_path)
        sys.exit(0)
        return
    
    with open(podfile_lock_file_path) as f:
        file_content = f.read()
        f.close()
    
    cocoapods_version = get_cocoapods_version(file_content)
    print(f"cocoapods_version = {cocoapods_version}") if args.debug else None
    PODS_components = get_PODS_components(cocoapods_version, file_content)
    get_shared_logger().debug(f"finish {PODS} section") if args.debug else None

    DEPENDENCIES_components = get_DEPENDENCIES_components(cocoapods_version, file_content)
    get_shared_logger().debug(f"finish {DEPENDENCIES} section") if args.debug else None

    SPEC_CHECKSUMS_components = get_SPEC_CHECKSUMS_components(cocoapods_version, file_content)
    get_shared_logger().debug(f"finish {SPEC_CHECKSUMS} section") if args.debug else None

    pod_version_dict= get_pod_version_dict(PODS_components, DEPENDENCIES_components)

    if args.json_output_file and args.json_output_file.strip():
        out_file = open(args.json_output_file, "w")
        json_list = [
            { PODS: PODS_components },
            { DEPENDENCIES: DEPENDENCIES_components },
            { SPEC_CHECKSUMS: SPEC_CHECKSUMS_components },
            { POD_VERSIONS: pod_version_dict },
        ]
        out_file.writelines(json.dumps(json_list))
        out_file.close()

    if isinstance(args.query_pod_list, list):
        pod_dict = {}
        pod_list = args.query_pod_list
        for x in pod_list:
            if x in pod_version_dict:
                pod_dict[x] = pod_version_dict[x]
        output = json.dumps(pod_dict)
        sys.stdout.write(output)
    
    return


def run_command_parser():
    my_parser = argparse.ArgumentParser(description='Parse the Podfile.lock file')
    my_parser.add_argument('-p', '--path', help='The path of Podfile.lock file', required=True)
    my_parser.add_argument('-d', '--debug', action='store_true', help='The debug mode')
    my_parser.add_argument('-j', '--json-output-file', help='The path of output JSON file', required=False)
    my_parser.add_argument('-q', '--query-pod-list', action='store', type=str, nargs='+')
    args = my_parser.parse_args()
    return args


def main():
    args = run_command_parser()
    run_podfile_lock_file_parser(args.path, args)


if __name__ == '__main__':
    sys.exit(main())
