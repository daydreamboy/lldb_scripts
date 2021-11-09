
"""
a script for ignore specific exception

Usage:
1. place this script at ~/lldb
2. create an All Objective-C Exceptions breakpoint by Xcode
3. add a new Debugger Command, and type the formatted command

ignore_specified_objc_exceptions name:<exception name1> name:<exception name2> ...

@see https://stackoverflow.com/a/19262247
"""

import lldb
import re
import shlex

gFlagVerbose = True
gLogTag = 'lld_scripts'

# This script allows Xcode to selectively ignore Obj-C exceptions
# based on any selector on the NSException instance


def get_register_name(target):
    if target.triple.startswith('x86_64'):
        return "rdi"
    elif target.triple.startswith('i386'):
        return "eax"
    elif target.triple.startswith('arm64'):
        return "x0"
    else:
        return "r0"


def call_method_on_exception(frame, register, method):
    return frame.EvaluateExpression(
        "(NSString *)[(NSException *)${0} {1}]".format(register, method)).GetObjectDescription()


def handle_call(debugger, user_input, result, unused):
    target = debugger.GetSelectedTarget()
    frame = target.GetProcess().GetSelectedThread().GetFrameAtIndex(0)

    if frame.symbol.name != 'objc_exception_throw':
        # We can't handle anything except objc_exception_throw
        output = "[{0}] Unable to handle none objc exception; ignoring...".format(gLogTag)
        result.PutCString(output)
        result.flush()
        return None

    # Note: user_input is the string after the command ignore_specified_objc_exceptions
    filterKeyValuePairs = shlex.split(user_input)

    register = get_register_name(target)

    for filterKeyValuePair in filterKeyValuePairs:
        method, regexp_str = filterKeyValuePair.split(":", 1)
        value = call_method_on_exception(frame, register, method)

        if value is None:
            output = "[{0}] Unable to grab exception from register {1} with method {2}; skipping...".format(gLogTag, register, method)
            result.PutCString(output)
            result.flush()
            continue

        regexp = re.compile(regexp_str)

        if regexp.match(value):
            output = "[{0}] Skipping exception because exception's {1} ({2}) matches {3}".format(gLogTag, method, value, regexp_str)
            result.PutCString(output)
            result.flush()

            # If we tell the debugger to continue before this script finishes,
            # Xcode gets into a weird state where it won't refuse to quit LLDB,
            # so we set async so the script terminates and hands control back to Xcode
            debugger.SetAsync(True)
            debugger.HandleCommand("continue")
            return None

    return None


def __lldb_init_module(debugger, unused):
    """Initialize the ignore_specified_objc_exceptions command within lldb"""

    debugger.HandleCommand('command script add --function ignore_specified_objc_exceptions.handle_call ignore_specified_objc_exceptions')

    print('The "ignore_specified_objc_exceptions" command has been loaded and is ready for use.')

