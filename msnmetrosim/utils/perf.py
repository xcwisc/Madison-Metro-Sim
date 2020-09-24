"""Function to measure the performance."""
import inspect
import time
from dataclasses import dataclass
from typing import Any, Union, List

__all__ = ("time_function",)


@dataclass
class TimingResult:
    """Function execution timing result."""

    return_: Any
    execution_ns: int
    caller_stack: inspect.FrameInfo

    @property
    def execution_us(self) -> float:
        """Get the time spent on the execution in microseconds (us)."""
        return self.execution_ns / 1000

    @property
    def execution_ms(self) -> float:
        """Get the time spent on the execution in milliseconds (ms)."""
        return self.execution_us / 1000

    def __repr__(self):
        return f"{self.execution_us:.2f} us - " \
               f"Line {self.caller_stack.lineno} {self.caller_stack.function} in {self.caller_stack.filename}"


def time_function(fn, *args, log: bool = True, count: int = 1, **kwargs) -> Union[List[TimingResult], TimingResult]:
    """
    Time the function execution and returns :class:`ExecutionResult`.

    If ``log`` is ``True``, the function execution time
    and the function location will also being printed out to ``stdout``.

    ``count`` must be > 0.

    If ``count`` = 1, the return will be a single :class:`TimingResult`.

    If ``count`` > 1, the return will be a list of :class:`TimingResult`.

    Usage:

    >>> def func(num):
    >>>     # code to be timed
    >>>
    >>> def main():
    >>>     result = time_function(func, 7)

    :param fn: function to be timed
    :param log: if the execution result should be logged
    :param count: repetitive count of function execution
    :param args: args for `fn`
    :param kwargs: kwargs for `fn`
    """
    _start_ = time.time_ns()
    ret = fn(*args, **kwargs)

    if count == 1:
        exec_result = TimingResult(return_=ret, execution_ns=time.time_ns() - _start_,
                                   caller_stack=inspect.stack()[1])
    else:
        exec_result = [TimingResult(return_=ret, execution_ns=time.time_ns() - _start_,
                                    caller_stack=inspect.stack()[1]) for _ in range(count)]

    if log:
        print(exec_result)

    return exec_result
