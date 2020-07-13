
from __future__ import print_function
import lldb
import os
import json


def handle_call(debugger, raw_args, result, internal_dict):
    """Receives and handles the call to write from lldb"""
    config_filepath = os.path.expanduser('~/simulator_debug.json')

    if not os.path.exists(config_filepath):
        return

    with open(config_filepath, 'r') as file:
        separators = (',', ':')
        json_object = json.load(file)
        json_string = json.dumps(json.dumps(json_object, indent=None, separators=separators, sort_keys=True))

    s = '@import Foundation;' \
        'NSString *filePath = NSHomeDirectory();' \
        'filePath = [filePath stringByAppendingPathComponent:@"Documents/simulator_debug.json"];' \
        '[[NSFileManager defaultManager] createFileAtPath:filePath contents:[@{0} dataUsingEncoding:4] attributes:nil];' \
        ''.format(json_string)

    res = lldb.SBCommandReturnObject()
    interpreter = lldb.debugger.GetCommandInterpreter()

    interpreter.HandleCommand("exp -l objc -O -- " + s, res)

    output = res.GetOutput() or res.GetError()
    #print(res)
    #print(output, end='')


def __lldb_init_module(debugger, internal_dict):
    """Initialize the config command within lldb"""
    debugger.HandleCommand('command script add -f %s.handle_call config' % os.path.splitext(os.path.basename(__file__))[0])
    print('The "config" command has been loaded and is ready for use.')

    # print("exp -l objc -O -- " + s)
