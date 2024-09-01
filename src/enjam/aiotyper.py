import asyncio
import inspect
from functools import wraps, partial

from typer import Typer


class AsyncTyper(Typer):
    """ Supports sync and async commands. """

    @staticmethod
    def maybe_run_async(decorator, func):
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            def runner(*args, **kwargs):
                return asyncio.run(func(*args, **kwargs))

            decorator(runner)
        else:
            decorator(func)
        return func

    def callback(self, *args, **kwargs):
        decorator = super().callback(*args, **kwargs)
        return partial(self.maybe_run_async, decorator)

    def command(self, *args, **kwargs):
        decorator = super().command(*args, **kwargs)
        return partial(self.maybe_run_async, decorator) 
