#!/usr/bin/python3
# -*- coding: UTF-8 -*-

from optparse import OptionParser
from urllib.request import urlopen

import lldb
import os
import json
import lldbutil
import shlex
import subprocess


failedLibs = set()


def show_source_code(debugger, command, result, internal_dict):
    global failedLibs
    
    command_args = shlex.split(command)

    parser = OptionParser()

    parser.add_option("-f", "--frame", action="store_true", default=True,
                      help="current frame source code debug")

    parser.add_option("-p", "--process",
                      action="store_true", default=False,
                      help="process all threads frames source code mapping")

    parser.add_option("-t", "--thread",
                      action="store_true", default=False,
                      help="current thread all frames source code mapping")

    parser.add_option("-c", "--clean", action="store_true", default=False,
                      help="clean global memory data, e.g. env file")

    parser.add_option("-d", "--debug", action="store_true", default=False,
                      help="current frame source code debug")

    (options, args) = parser.parse_args(command_args)

    debugger.HandleCommand('settings set frame-format ${function.name}')
    state = lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame().GetDisplayFunctionName()
    executable_path = debugger.GetSelectedTarget().GetExecutable().GetDirectory()
    print("executablePath: " + executable_path)

    if options.thread:
        print("process all frames target source map")
        thread_all_frame_map(executable_path, debugger)
    elif options.process:
        print("thread all frames target source map")
        process_all_frame_map(executable_path, debugger)
    elif options.clean:
        globals().pop('_show_source_code_env', None)
        print("Done!🍺🍺🍺")
    else:
        ci = debugger.GetCommandInterpreter()
        res = lldb.SBCommandReturnObject()
        ci.HandleCommand('source info', res)
        source_info = res.GetOutput(True)

        if source_info is None:
            print('Error: No debug info for the selected frame')
            return
        success = target_source_map(source_info, executable_path, debugger)
        print(f'[Error] mapping {source_info} failed') if success is False else None


def get_pod_info_dict(source_info):
    """This method get pod info into a dictionary with keys: pod_name、build_UUID"""

    # Note: the parse Pod info is customizable, not general way
    # e.g. ['', 'Users', 'username', '<sentinel>', '<PodName>', 'Classes', 'yyy', 'zzz.m:12']
    source_file_path_component_list = source_info.split(': ').pop().split('/')

    # Note: sentinel is the string which before the pod name, for example, /.../x/PodName/...,
    # the x is sentinel
    sentinel_list = get_env_dict()['pod_name_sentinel'].strip(' \'"').split(',')

    for sentinel in sentinel_list:
        sentinel = sentinel.strip()
        if sentinel in source_file_path_component_list:
            index_before_pod = source_file_path_component_list.index(sentinel)
            break

    if index_before_pod is None:
        print(f"Error: not find pod with source info: {source_info}")
        return None
    
    pod_name = source_file_path_component_list[index_before_pod + 1]
    # Note: e.g. /Users/username/build/to/path/DGFoundation
    pod_build_prefix = '/'.join(source_file_path_component_list[0:index_before_pod + 2])
    info_dict = {
        'pod_name': pod_name,
        'pod_build_prefix': pod_build_prefix,
    }
    return info_dict


def get_pod_version(pod_name, executable_path):
    derived_data_path = '/'.join(executable_path.split('/')[0:8])
    print("derivedDataPath: " + derived_data_path)

    podfile_lock_file_path = get_podfile_lock_file_path(derived_data_path)
    if podfile_lock_file_path is None or not os.path.isfile(podfile_lock_file_path):
        return None
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'parse_podfile_lock_file.py')
        output = subprocess.check_output(
            ['python3', f'{script_path}', '-p', f'{podfile_lock_file_path}', '-q', f'{pod_name}'])
        output = output.decode('utf-8')
        print(f"local pod version: `{output}`")
    except subprocess.CalledProcessError as e:
        print("Command execution failed!")
    pod_dict = json.loads(output)
    if pod_name in pod_dict:
        pod_version = pod_dict[pod_name]
        return pod_version

    return None


def get_podfile_lock_file_path(derived_data_path):
    """get the Podfile.lock file path"""
    info_plist_path = os.path.join(derived_data_path, 'info.plist')
    if not os.path.isfile(info_plist_path):
        return None

    print(f'info_plist_path: {info_plist_path}')
    # Note: info.plist is special, can't open as text using Xcode builtin Python3.9
    output = subprocess.check_output(['xcrun', 'defaults', 'read', f'{info_plist_path}', 'WorkspacePath'])
    # Note: there are some tricks here
    # 1. decode('utf-8') for xml info.plist
    # 2. encode('utf-8').decode('unicode_escape') try to fix \uXXX when the path contains chinese characters
    output = output.decode('utf-8').encode('utf-8').decode('unicode_escape')
    xcodeproj_or_workspace_path = output.strip('\n ')

    if xcodeproj_or_workspace_path is None:
        return None

    print(f'xcodeproj_or_workspace_path: {xcodeproj_or_workspace_path}')

    podfile_lock_file_path = os.path.join(os.path.dirname(xcodeproj_or_workspace_path), 'Podfile.lock')
    print(f'Podfile.lock: {podfile_lock_file_path}')

    return podfile_lock_file_path


def get_env_dict():
    if '_show_source_code_env' in globals():
        return globals()['_show_source_code_env']

    env_file_path = os.path.join(os.path.dirname(__file__), '.env')
    props = {}

    # @see https://stackoverflow.com/questions/19799522/python-how-to-create-a-dictionary-from-properties-file-while-omitting-comments
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()  # removes trailing whitespace and '\n' chars

            if "=" not in line: continue  # skips blanks and comments w/o =
            if line.startswith("#"): continue  # skips comments which contain =

            k, v = line.split("=", 1)
            # Note: make all keys lowercase for convenience
            props[k.strip().lower()] = v.strip()
    globals()['_show_source_code_env'] = props

    return props


def get_git_info_dict(pod_name, pod_version):
    podspec_file_path = f'/tmp/show_source_code/{pod_name}-{pod_version}.json'
    env_dict = get_env_dict()
    content_dict = {}

    # Note: if SNAPSHOT version always query server to get latest podspec
    if os.path.isfile(podspec_file_path) and 'snapshot' not in pod_version.lower():
        with open(podspec_file_path) as f:
            content = f.read()
            content_dict = json.loads(content)
            f.close()

    if len(content_dict) == 0:
        url = env_dict['podspec_query_api'].strip(" '\"")
        formatted_url = url.format(pod_name=pod_name, pod_version=pod_version)
        print(f'request url: {formatted_url}')
        content = urlopen(formatted_url).read()
        content_dict = json.loads(content)
    else:
        print(f'Use cached podspec: {podspec_file_path}')

    git_url_key = env_dict['git_url_keypath'].strip(" '\"")
    git_commit_key = env_dict['git_commit_keypath'].strip(" '\"")

    dict_value = {
        'git_url': tool_get_value_by_key_path(content_dict, git_url_key),
        'git_commit': tool_get_value_by_key_path(content_dict, git_commit_key),
    }

    os.makedirs(os.path.dirname(podspec_file_path), exist_ok=True)
    with open(podspec_file_path, "w") as f:
        f.write(json.dumps(content_dict))
        f.close()

    return dict_value


def download_git_repo(git_url, git_commit, pod_name, pod_version):
    download_dir = os.path.join('/tmp/show_source_code', pod_name, pod_version)
    #download_file_path = os.path.join(download_dir, 'download.tar')

    if not os.path.exists(download_dir):
        # Note: this way not works
        # @see https://stackoverflow.com/questions/11018411/how-do-i-export-a-specific-commit-with-git-archive
        #git_download_cmd = f"git archive --remote={git_url} {git_commit} > {download_file_path}"
        #unarchive_cmd = f'cd {download_dir}; tar -xvf {download_file_path}'
        #print(f'execute `{git_download_cmd}`')
        #print(f'execute `{unarchive_cmd}`')

        os.system(f'mkdir -p {download_dir}')
        print(f'download_git_repo: {download_dir}')
        os.system(f'cd {download_dir}; git init; git remote add origin {git_url}; git fetch --depth 1 origin {git_commit}; git checkout FETCH_HEAD')

    return download_dir


def get_saved_map_string(source_map_file_path, current_local_source_code_prefix):
    map_string_lines = []
    if os.path.isfile(source_map_file_path):
        with open(source_map_file_path, "r") as f:
            seen_set = set()
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                line = line.strip(' \n')
                if len(line) == 0:
                    continue
                components = line.split(' ')
                if len(components) != 2:
                    continue
                path = components[1]
                if os.path.exists(path):
                    if path != current_local_source_code_prefix and line not in seen_set:
                        print(f'use cached map: `{line}`')
                        seen_set.add(line)
                        map_string_lines.append(line)
    return map_string_lines


def tool_get_value_by_key_path(data, key_path):
    keys = key_path.split('.')
    value = data
    for key in keys:
        value = value.get(key)
        if value is None:
            break
    return value


def target_source_map(source_info, executable_path, debugger):
    print("source_info: " +  source_info)
    source_file_path = source_info.split(": ").pop().split(':')[0]

    if os.path.isfile(source_file_path):
        print('[show_source_code] No binary need to debug. Source code is already available.')
        return True
    else:
        print(f"env_info: {get_env_dict()}")

        pod_info_dict = get_pod_info_dict(source_info)
        if pod_info_dict is None:
            print(f"source info parse failed: {source_info}")
            return False

        print(f"pod_info: {pod_info_dict}")
        pod_name = pod_info_dict['pod_name']
        pod_build_prefix = pod_info_dict['pod_build_prefix']
        print(f'podName: {pod_name}')
        pod_version = get_pod_version(pod_name, executable_path)
        if pod_version is None:
            print(f'pod version query failed with pod name {pod_name}')
            return False

        git_info = get_git_info_dict(pod_name, pod_version)
        git_url = git_info['git_url']
        git_commit = git_info['git_commit']
        print(f"git_info: {git_info}")

        local_source_code_prefix = os.path.join(download_git_repo(git_url, git_commit, pod_name, pod_version), pod_name)
        new_map_string = f'{pod_build_prefix} {local_source_code_prefix}'

        source_map_file_path = os.path.join('/tmp/show_source_code', 'source_map.txt')
        lines = get_saved_map_string(source_map_file_path, local_source_code_prefix)
        print(f'lines: {lines}')

        lines.append(new_map_string)

        map_string = ' '.join(lines)
        source_map_cmd = f'settings set target.source-map {map_string}'
        print(f'execute: {source_map_cmd}')
        print('Starting translate into source code...')
        debugger.HandleCommand(source_map_cmd)

        with open(source_map_file_path, "w") as f:
            f.write('\n'.join(lines))
            f.close()

        print('Done!🍺🍺🍺')

        return True


def process_all_frame_map(executable_path, debugger):
    hasOneFailed = False

    for thread in lldb.debugger.GetSelectedTarget().GetProcess():
        lineEntries = lldbutil.get_file_specs(thread)
        for lineEntry in lineEntries:
            if lineEntry.GetDirectory() is not None and lineEntry.GetFilename() is not None:
                path = lineEntry.GetDirectory() + "/" + lineEntry.GetFilename()
                success = target_source_map(path, executable_path, debugger)
                print(f'[Error] mapping {path} failed') if success is False else None
                if not hasOneFailed and not success:
                    hasOneFailed = not success

    if not hasOneFailed:
        print('Done!🍺🍺🍺')


def thread_all_frame_map(executable_path, debugger):
    hasOneFailed = False

    thread = lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread()
    lineEntries = lldbutil.get_file_specs(thread)
    for lineEntry in lineEntries:
        if lineEntry.GetDirectory() is not None and lineEntry.GetFilename() is not None:
            path = lineEntry.GetDirectory() + "/" + lineEntry.GetFilename()
            success = target_source_map(path, executable_path, debugger)
            print(f'[Error] mapping {path} failed') if success is False else None
            if not hasOneFailed and not success:
                hasOneFailed = not success

    if not hasOneFailed:
        print('Done!🍺🍺🍺')


def preload_map_info_on_lldb_start(debugger):
    source_map_file_path = os.path.join('/tmp/show_source_code', 'source_map.txt')
    lines = get_saved_map_string(source_map_file_path, '')
    if len(lines) == 0:
        return 
    print(f'lines: {lines}')
    map_string = ' '.join(lines)
    source_map_cmd = f'settings set target.source-map {map_string}'
    print(f'execute: {source_map_cmd}')
    debugger.HandleCommand(source_map_cmd)


def __lldb_init_module(debugger, internal_dict):
    # Note: keep the file name with format `lldb_command_xxx` which xxx is the lldb command
    prefix = 'lldb_command_'
    filename = os.path.splitext(os.path.basename(__file__))[0]
    command_name = filename.replace(prefix, '')
    debugger.HandleCommand(f'command script add --help "二进制源码调试" -f {filename}.show_source_code {command_name}')
    print(f'The "{command_name}" command has been installed and is ready for use.')

    preload_map_info_on_lldb_start(debugger)

