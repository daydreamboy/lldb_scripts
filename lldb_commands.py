##
# The loader script for lldb_commands.txt
#
# Usage:
# put the following line in ~/.lldbinit file
#
# command script import ~/lldb_scripts/lldb_commands.py
#
# Reference:
# @see https://github.com/DerekSelander/LLDB/blob/master/lldb_commands/dslldb.py

import lldb
import os


def __lldb_init_module(debugger, internal_dict):
    file_path = os.path.realpath(__file__)
    dir_name = os.path.dirname(file_path)
    load_python_scripts_dir(dir_name)


def load_python_scripts_dir(dir_name):
    this_files_basename = os.path.basename(__file__)
    cmd = ''
    for file in os.listdir(dir_name):
        if file.endswith('.py'):
            cmd = 'command script import '
        elif file.endswith('.txt'):
            cmd = 'command source -e0 -s1 '
        else:
            continue

        if file != this_files_basename:
            fullpath = dir_name + '/' + file
            lldb.debugger.HandleCommand(cmd + fullpath)
