#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##
# 
# command script import ~/lldb_scripts/example/01_use_stop_hook/use_stophook.py

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
      self.symbol_name = extra_args.GetValueForKey("symbol").GetStringValue(100)
      print("[stop-hook] get symbol:", self.symbol_name)

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
      symbol_name = current_frame.GetSymbol().GetName()

      # Note: If the breakpoint for self.symbol_name is hitting, just ignore this  
      # breakpoint and continue. Otherwise, keep the stop for other breakpoints
      if symbol_name is not None and symbol_name == self.symbol_name:
        should_stop = False
        print(f'[stop-hook] matching symbol: {self.symbol_name} and continue the program')
        #symbol_contexts = target.FindGlobalFunctions(self.symbol_name, 0, lldb.eMatchTypeNormal)
        context = current_frame.GetSymbolContext(lldb.eSymbolContextEverything)
        line_number = current_frame.GetLineEntry().GetLine()
        source_file_path = context.GetCompileUnit().GetFileSpec()
        print(f"[stop-hook] symbol source file: {source_file_path}:{line_number}")

          # if lineEntry is not None:
          #    print(f"[stop-hook] symbol source: {str(lineEntry.GetFileSpec())}:{lineEntry.GetLine()}")
          #    print(f"[stop-hook] symbol source2: {lineEntry}")
          #    local_source_path = os.path.dirname(__file__)
          #    print(f"-> Local Source:  {local_source_path}")

      else:
        should_stop = True
        print(f'[stop-hook] target `{target}` stopped at symbol: {symbol_name}')

      return should_stop


def __lldb_init_module(debugger, internal_dict):
    filename = os.path.splitext(os.path.basename(__file__))[0]
    debugger.HandleCommand(f'target stop-hook add -P {filename}.StopHook -k "symbol" -v "globalFunc"')
    print(f'The stop-hook has been enabled')
  