# asio-debugger-extensions

GDB and LLDB debugger extensions for use with [Asio](https://github.com/chriskohlhoff/asio)
and [Boost.Asio](https://github.com/boostorg/asio). 

## Pretty Printing

Pretty printing is supported for the following `asio::` and `boost::asio::`
types when using GDB:

* `execution::any_executor<...>`
* `any_completion_executor`
* `any_io_executor`
* `io_context::executor_type` and related executor types

## Awaitable Backtrace

The `abt` command may be used to produce a backtrace or call stack for coroutines
that use the `asio::awaitable` or `boost::asio::awaitable` templates for their
return types.

For example, given the program:

```cpp
#include <asio.hpp>
#include <chrono>
#include <iostream>

asio::awaitable<void> inner()
{
  asio::steady_timer timer(co_await asio::this_coro::executor);
  for (int i = 0; i < 10; ++i)
  {
    timer.expires_after(std::chrono::seconds(1));
    co_await timer.async_wait(asio::use_awaitable);
    std::cout << i << "\n"; // SET BREAKPOINT HERE
  }
}

asio::awaitable<void> middle()
{
  co_return co_await inner();
}

asio::awaitable<void> outer()
{
  for (int i = 0; i < 10; ++i)
    co_await middle();
}

int main()
{
  asio::io_context ctx;
  co_spawn(ctx, outer(), asio::detached);
  ctx.run();
}
```

running the `abt` command when stopped at the breakpoint will produce output
similar to the following:

```
(lldb) abt
frame #0 0x0000000100021ea0 inner() at example.cpp:6
frame #1 0x0000000100023510 middle() at example.cpp:17
frame #2 0x0000000100024150 outer() at example.cpp:22
frame #3 0x0000000100025a90 asio::awaitable<void, asio::any_io_executor>
  asio::detail::co_spawn_entry_point<asio::any_io_executor,
  asio::detail::awaitable_as_function<void, asio::any_io_executor>,
  asio::detail::detached_handler>(asio::awaitable<void, asio::any_io_executor>*,
  asio::any_io_executor, asio::detail::awaitable_as_function<void,
  asio::any_io_executor>, asio::detail::detached_handler) at co_spawn.hpp:119
```
