#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##
# Two usage of this script
#
# Usage1 - Configure this script with specific search_symbol_name
# Step 1: place this script file in your source code repo root folder
# Step 2: add this line to ~/.lldbinit
#         command script import ~/path/to/use_stophook.py
# Step 3: change search_symbol_name to your symbolic breakpoint, and make a symbolic breakpoint
# Step 4: run Xcode
#
# Usage2 - Configure specific search_symbol_name in .lldbinit file
#
# 

# Usage1
#search_symbol_name = 'globalFunc'
#
# Usage2
search_symbol_name = None

"""
This script demonstrates the usage of stop-hook
"""

import lldb
import os

class StopHook:
    """
    target: The target that the stop hook is being added to.
    extra_args: An SBStructuredData Dictionary filled with the -key -value
                option pairs passed to the command.
    dict: An implementation detail provided by lldb.
    """
    def __init__(self, target, extra_args, internal_dict):
      self.source_mapped = False
      self.symbol_name = extra_args.GetValueForKey("symbol").GetStringValue(100)
      self.repo_root_path = extra_args.GetValueForKey("repo_root").GetStringValue(100)
      print("[stop-hook] get symbol:", self.symbol_name)
      print("[stop-hook] repo root:", self.repo_root_path)

    """
    exe_ctx: An SBExecutionContext for the thread that has stopped.
    stream: An SBStream, anything written to this stream will be printed in the
            the stop message when the process stops.
    Return Value: The method returns "should_stop".  If should_stop is false
                  from all the stop hook executions on threads that stopped
                  with a reason, then the process will continue.  Note that this
                  will happen only after all the stop hooks are run.
    """
    def handle_stop(self, exe_ctx, stream):
      target = exe_ctx.GetTarget()
      current_frame = exe_ctx.GetFrame()
      current_symbol_name = current_frame.GetSymbol().GetName()
      tidied_current_symbol_name = current_symbol_name if current_symbol_name.find('(') == -1 else current_symbol_name.split('(')[0]

      # Note: If the breakpoint for self.symbol_name is hitting, just ignore this  
      # breakpoint and continue. Otherwise, keep the stop for other breakpoints
      if current_symbol_name is not None and (current_symbol_name == self.symbol_name or tidied_current_symbol_name == self.symbol_name):
        should_stop = False

        if self.source_mapped:
           print(f'[stop-hook] source map is already done, just skip it.')
           return should_stop

        print(f'[stop-hook] matching symbol: {self.symbol_name} and continue the program')
        #symbol_contexts = target.FindGlobalFunctions(self.symbol_name, 0, lldb.eMatchTypeNormal)
        context = current_frame.GetSymbolContext(lldb.eSymbolContextEverything)
        line_number = current_frame.GetLineEntry().GetLine()
        source_file_path = f"{context.GetCompileUnit().GetFileSpec()}"
        file_name = os.path.basename(source_file_path)

        print(f"[stop-hook] compiled symbol source file: {source_file_path}:{line_number}")

        local_source_file_path = self.search_file_path(self.repo_root_path, file_name)
        if local_source_file_path:
           print(f"[stop-hook] local symbol source file: {local_source_file_path}")

           common_suffix, compiled_prefix, local_prefix = self.find_common_suffix(source_file_path, local_source_file_path)
           print(f"[stop-hook] compiled_prefix: {compiled_prefix}")
           print(f"[stop-hook] local_prefix: {local_prefix}")
           target.GetDebugger().HandleCommand("settings set target.source-map '%s' '%s'" % (compiled_prefix, local_prefix))
        else:
           print(f'[stop-hook] not find file: {file_name}')

        self.source_mapped = True
      else:
        should_stop = True
        print(f'[stop-hook] target `{target}` stopped at symbol: {current_symbol_name}')

      return should_stop
    
    """
    Utility
    """
    def search_file_path(self, directory_path, target_filename):
      directory_path = os.path.expanduser(directory_path)
      for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file == target_filename:
                file_path = os.path.join(root, file)
                return file_path
      return None
    
    """
    Utility
    """
    def find_common_suffix(self, str1, str2):
      common_suffix = ""
      i = len(str1) - 1
      j = len(str2) - 1
    
      while i >= 0 and j >= 0 and str1[i] == str2[j]:
        common_suffix = str1[i] + common_suffix
        i -= 1
        j -= 1
    
      return common_suffix, str1[:i+1], str2[:j+1]


def __lldb_init_module(debugger, internal_dict):
    filename = os.path.splitext(os.path.basename(__file__))[0]
    if search_symbol_name: 
       debugger.HandleCommand(f'target stop-hook add -P {filename}.StopHook -k "symbol" -v "{search_symbol_name}"')
       print(f'The stop-hook has been enabled and waiting for symbol `{search_symbol_name}`')
    else:
       print(f'The stop-hook has been enabled')
  