#
# Copyright (C) Halk-lai Liff <halkliff@pm.me> & Werberth Lins <werberth.lins@gmail.com>, 2018-present
# Distributed under GNU AGPLv3 License, found at the root tree of this source, by the name of LICENSE
# You can also find a copy of this license at GNU's site, as it follows <https://www.gnu.org/licenses/agpl-3.0.en.html>
#
# THIS SOFTWARE IS PRESENTED AS-IS, WITHOUT ANY WARRANTY, OR LIABILITY FROM ITS AUTHORS
# EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE.  THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM
# IS WITH YOU.  SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF
# ALL NECESSARY SERVICING, REPAIR OR CORRECTION.
#
# IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING
# WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS
# THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY
# GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE
# USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF
# DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD
# PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS),
# EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGES.
#

from concurrent.futures import ThreadPoolExecutor
from typing import Callable
import asyncio
from collections import OrderedDict
from functools import partial, wraps


__all__ = ['to_async', 'async_lru']


# Inspired by https://github.com/django/asgiref/blob/master/asgiref/sync.py
class to_async:
    """
    A helper class to create Awaitable functions from synchronous functions.
    """

    def __init__(self, func: Callable):
        self.func = func
        self.loop = asyncio.get_event_loop()
        self.loop.set_default_executor(ThreadPoolExecutor())

    async def __call__(self, *args, **kwargs):
        future = self.loop.run_in_executor(None, partial(self.func, *args, **kwargs))
        return await asyncio.wait_for(future, timeout=None)


# Inspired by <https://github.com/aio-libs/async_lru/blob/master/async_lru.py> and
# <https://wiki.python.org/moin/PythonDecoratorLibrary>
class async_lru:
    """
    A helper class to make LRU cache of async functions
    """
    cache = OrderedDict()

    # Copied from functools.py
    class hashed_seq(list):
        """
        This class guarantees that hash() will be called no more than once
        per element.  This is important because the lru_cache() will hash
        the key multiple times on a cache miss.
        """

        __slots__ = 'hash_value'

        def __init__(self, tup, hash_alg=hash):
            super(async_lru.hashed_seq, self).__init__(tup)
            self[:] = tup
            self.hash_value = hash_alg(tup)

        def __hash__(self):
            return self.hash_value

    def __init__(self, max_size: int):
        self.maxsize = max_size
        self.hits: int = 0
        self.misses: int = 0
        self.func: Callable = None
        self.tasks: set = set()
        self.loop = asyncio.get_event_loop()

    def __call__(self, func):
        if self.func is None or (self.func != func):
            self.func = func

        @wraps(self.func)
        async def decorator(*args, **kwargs):
            key = self._make_key(args, kwargs)

            future: asyncio.Task = self.cache.get(key, None)
            if future is not None:
                if not future.done():
                    self.hits += 1
                    return await asyncio.shield(future, loop=self.loop)
                exception = future.exception(True)
                if exception is None:
                    self.hits += 1
                    self.cache.move_to_end(key)
                    return future.result()

                # In case there happened an exception, it won't cache it.
                self.cache.pop(key)

            future = self.loop.create_future()
            coro = self.func(*args, **kwargs)
            task: asyncio.Task = asyncio.create_task(coro=coro)
            task.add_done_callback(partial(self._done_callback, future))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.remove)

            self.cache[key] = task

            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)

            self.misses += 1
            self.cache.move_to_end(key)

            return await asyncio.shield(future, loop=self.loop)
        return decorator

    # Copied from functools.py
    def _make_key(self, args, kwargs, typed=True,):
        """Make a cache key from optionally typed positional and keyword arguments

        The key is constructed in a way that is flat as possible rather than
        as a nested structure that would take more memory.

        If there is only a single argument and its data type is known to cache
        its hash value, then that argument is returned without a wrapper.  This
        saves space and improves lookup speed.

        """
        # All of code below relies on kwds preserving the order input by the user.
        # Formerly, we sorted() the kwds before looping.  The new way is *much*
        # faster; however, it means that f(x=1, y=2) will now be treated as a
        # distinct call from f(y=2, x=1) which will be cached separately.

        kwd_mark = (object(),),
        fasttypes = (int, str, frozenset, type(None))

        key = args
        if kwargs:
            key += kwd_mark
            for item in kwargs.items():
                key += item
        if typed:
            key += tuple(type(v) for v in args)
            if kwargs:
                key += tuple(type(v) for v in kwargs.values())
        elif len(key) == 1 and type(key[0]) in fasttypes:
            return key[0]
        return self.hashed_seq(key)

    @staticmethod
    def _done_callback(future: asyncio.Future, task: asyncio.Task):
        if task.cancelled():
            future.cancel()
            return

        exception = task.exception(True)
        if exception is not None:
            future.set_exception(exception)
            return

        future.set_result(task.result())

    def __repr__(self):
        return self.func.__doc__

    def __get__(self, instance, owner):
        return partial(self.__call__, instance)
