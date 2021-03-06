import asyncio
from contextlib import suppress
from functools import partial
import signal

from worker import Worker
from manager import Manager


class Runner:
    def __init__(self, workers_count, coroutine, duration=None, max_runs=None, max_runs_per_worker=None,
                 session_setup=None, loop=None):
        self.workers_count = workers_count
        self.coroutine = coroutine
        self.workers = []
        self.tasks = []
        self.manager = Manager(duration, max_runs, max_runs_per_worker)
        self.loop = loop or asyncio.get_event_loop()
        self.session_setup = session_setup

    def shutdown(self, signal, frame):
        self.manager.cancel()
        for task in self.tasks:
            with suppress(asyncio.CancelledError):
                task.cancel()
        self.tasks = []

    def ensure_future(self, coro):
        return asyncio.ensure_future(coro, loop=self.loop)

    def gather(self, *tasks):
        return asyncio.gather(*tasks, loop=self.loop, return_exceptions=True)

    def create_worker(self, wid):
        return Worker(self.loop, wid, self.coroutine, self.manager, self.session_setup)

    def setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        handler = partial(self.shutdown, None, None)
        self.loop.add_signal_handler(signal.SIGINT, handler)
        self.loop.add_signal_handler(signal.SIGTERM, handler)

    def run(self):
        self.setup_signal_handlers()

        workers = [self.create_worker(i) for i in range(self.workers_count)]
        tasks = [self.ensure_future(w.run()) for w in workers]
        tasks.append(self.ensure_future(self.manager.current_stats()))

        self.tasks = tasks
        try:
            self.loop.run_until_complete(self.gather(*tasks))
        finally:
            self.loop.close()
        return self.manager
