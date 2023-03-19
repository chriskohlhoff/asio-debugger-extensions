# Provides the ability to print the coroutine "call stack" for C++20 coroutines
# that use the 'asio::awaitable<>' type.
#
# Note: Currently supports programs compiled using gcc and clang.
#
# To use, add the following line to ~/.gdbinit:
#
#   source /path/to/awaitable_backtrace.py
#
# and then run the command 'abt' when stopped at a breakpoint inside an
# awaitable function.

import gdb
import re

class AwaitableBacktraceCommand(gdb.Command):
  "Print a backtrace for the current awaitable function."

  def __init__(self):
    super(AwaitableBacktraceCommand, self).__init__("abt", gdb.COMMAND_USER, gdb.COMPLETE_NONE, True)

  def _current_awaitable_frame(self):
    regex = re.compile(".*asio::detail::awaitable_frame_base<.*>::resume")
    curr_frame = gdb.newest_frame()
    while curr_frame is not None:
      if regex.match(curr_frame.name()) is not None:
        return curr_frame.read_var("this").dereference()
      curr_frame = curr_frame.older()
    return None

  @staticmethod
  def _coro_handle(coro):
    if "__handle_" in coro.type.fields():
      return coro["__handle_"]
    else:
      return coro["_M_fr_ptr"]

  def _print_coro(self, coro, depth):
    coro_data = self._coro_handle(coro).cast(gdb.lookup_type("void").pointer().pointer())
    address = int(coro_data.dereference().format_string(format="d"))
    block = gdb.block_for_pc(address)
    function_name = block.function.print_name
    location = gdb.find_pc_line(address)
    filename = location.symtab.filename
    line = location.line
    print(f"#{depth: <3} 0x{address:016x} {function_name} at {filename}:{line}")

  def _walk_awaitable_frames(self, frame, depth = 0):
    try:
      self._print_coro(frame["coro_"], depth)
      self._walk_awaitable_frames(frame["caller_"].dereference(), depth + 1)
    except gdb.error:
      pass

  def invoke(self, arg, from_tty):
    awaitable_frame = self._current_awaitable_frame()
    if awaitable_frame is not None:
      self._walk_awaitable_frames(awaitable_frame)
    else:
      print("not in an awaitable")

AwaitableBacktraceCommand()
