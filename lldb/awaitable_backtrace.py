# Provides the ability to print the coroutine "call stack" for C++20 coroutines
# that use the 'asio::awaitable<>' type.
#
# Note: Currently supports programs compiled using clang.
#
# To use, add the following line to ~/.lldbinit:
#
#   command script import /path/to/awaitable_backtrace.py
#
# and then run the command 'abt' when stopped at a breakpoint inside an
# awaitable function.

import lldb
import re

def current_awaitable_frame(target):
  regex = re.compile(".*asio::detail::awaitable_frame_base<.*>::resume()")
  for frame in target.GetProcess().selected_thread.frames:
    if regex.match(frame.name) is not None:
      return frame.FindVariable("this").deref
  return None

def print_coro(target, coro, depth):
  voidpp = target.FindFirstType("void").GetPointerType().GetPointerType()
  coro_data = coro.GetChildMemberWithName("__handle_").Cast(voidpp)
  address = coro_data.deref.GetValueAsAddress()
  symbol_address = target.ResolveLoadAddress(address)
  symbol = target.ResolveSymbolContextForAddress(symbol_address, lldb.eSymbolContextEverything)
  function_name = symbol.function.name
  filename = symbol.line_entry.file.basename
  line = symbol.line_entry.line
  print(f"frame #{depth} 0x{address:016x} {function_name} at {filename}:{line}")

def walk_awaitable_frames(target, frame, depth = 0):
  print_coro(target, frame.GetChildMemberWithName("coro_"), depth)
  caller = frame.GetChildMemberWithName("caller_")
  if caller.IsValid() and caller.GetValueAsUnsigned() != 0:
    walk_awaitable_frames(target, caller.deref, depth + 1)

def awaitable_backtrace(debugger, command, result, internal_dict):
  target = debugger.GetSelectedTarget()
  awaitable_frame = current_awaitable_frame(target)
  if awaitable_frame is not None:
    walk_awaitable_frames(target, awaitable_frame)
  else:
    print("not in an awaitable")

def __lldb_init_module(debugger, internal_dict):
  debugger.HandleCommand('command script add -f awaitable_backtrace.awaitable_backtrace abt')
