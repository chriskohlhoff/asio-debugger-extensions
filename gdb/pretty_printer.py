# Provides gdb pretty printing for various asio types.
#
# To use, add the following line to ~/.gdbinit:
#
#   source /path/to/pretty_printer.py

import gdb.printing
import re


class AnyExecutor(object):
  _target_re = (r"^<(boost::)*asio::execution::detail::any_executor_base::"
                "target_fns_table<(.*) *>\(bool, std::enable_if<!std::is_same<"
                ".*>::value, void>::type\*\)::fns_with_(blocking_)*execute>$")

  def __init__(self, value):
    self.type = value.type.strip_typedefs()
    self.target = self._target(value)

  def _target(self, value):
    if value["target_fns_"]:
      target_fns = value["target_fns_"].format_string(address=False)
      target_type_name = re.search(self._target_re, target_fns).group(2)
      target_type_name = re.sub(r"(\b[0-9]+)ul*\b", "\\1", target_type_name)
      target_type = gdb.lookup_type(target_type_name).strip_typedefs()
      return value["target_"].cast(target_type.pointer()).referenced_value()
    else:
      return None

  def to_string(self):
    if not self.target:
      return "%s [no target]" % self.type.name
    return "%s targeting %s" % (self.type.name, self.target.type.name)

  def children(self):
    if self.target:
      yield "[target]", self.target


class IoContextExecutor(object):
  _context_re = r"^(boost::)*(asio::io_context)::basic_executor_type<.*$"
  _context_mask = 0xfffffffffffffffc
  _blocking_never = 1
  _relationship_continuation = 2
  _outstanding_work_tracked = 4
  _runtime_bits = 3

  def __init__(self, value):
    self.context = self._context(value)
    self.bits = self._bits(value)
    self.allocator = self._allocator(value)

  def _context(self, value):
    match = re.search(self._context_re, value.type.strip_typedefs().name)
    context_name = (match.group(1) if match.group(1) else "") + match.group(2)
    context_type = gdb.lookup_type(context_name)
    return (value["target_"] & self._context_mask).cast(context_type.pointer())

  def _bits(self, value):
    static_bits = value.type.strip_typedefs().template_argument(1)
    runtime_bits = value["target_"] & self._runtime_bits
    return int((static_bits | runtime_bits).format_string())

  def _allocator(self, value):
    allocator_type = value.type.strip_typedefs().template_argument(0)
    return value.address.cast(allocator_type.pointer()).referenced_value()

  def children(self):
    yield "io_context", self.context
    yield "allocator", self.allocator
    yield "blocking", "never" if self.bits & self._blocking_never else "possibly"
    yield "relationship", "continuation" if self.bits & self._relationship_continuation else "fork"
    yield "outstanding_work", "tracked" if self.bits & self._outstanding_work_tracked else "untracked"


def build_pretty_printer():
  pp = gdb.printing.RegexpCollectionPrettyPrinter("asio")
  pp.add_printer("any_executor", r"^(boost::)*asio::execution::any_executor<.*$", AnyExecutor)
  pp.add_printer("any_completion_executor", r"^(boost::)*asio::any_completion_executor$", AnyExecutor)
  pp.add_printer("any_io_executor", r"^(boost::)*asio::any_io_executor$", AnyExecutor)
  pp.add_printer("io_context executor", r"^(boost::)*asio::io_context::basic_executor_type<.*$", IoContextExecutor)
  return pp


gdb.printing.register_pretty_printer(gdb.current_objfile(), build_pretty_printer())
