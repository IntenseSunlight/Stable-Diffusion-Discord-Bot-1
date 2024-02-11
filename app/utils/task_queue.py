import threading
import discord
import logging
import atexit
import random
from queue import Queue
from typing import Callable, Any, List, Dict, cast

from app.settings import Settings

__all__ = ["TaskState", "Task", "TaskQueue"]


class TaskState:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Task:

    def __init__(
        self,
        func: Callable,
        task_owner: discord.Member,
        *,
        task_id: int = None,
        args: List = [],
        kwargs: Dict = {},
    ):
        self.func = func
        self._task_id = task_id
        self._task_owner = task_owner
        self._state: TaskState = TaskState.PENDING
        self._result: Any = None
        self.args: List = args
        self.kwargs: Dict = kwargs
        self._cond = threading.Condition()

    def __repr__(self):
        return (
            f"<Task {self.func.__name__} owner={self.task_owner}, state={self.state}>"
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Task):
            return self._task_id == other._task_id
        return False

    @property
    def task_owner(self):
        return self._task_owner

    @property
    def state(self) -> TaskState:
        return self._state

    @state.setter
    def state(self, value: TaskState):
        self._state = value

    @property
    def result(self) -> Any:
        return self._result

    @result.setter
    def result(self, value: Any):
        self._result = value

    def cancel(self):
        if self.state in [TaskState.RUNNING, TaskState.COMPLETED, TaskState.FAILED]:
            return False

        self._state = TaskState.CANCELLED
        return True

    def run(self):
        if self.state == TaskState.COMPLETED:
            return True
        elif self.state == TaskState.CANCELLED:
            return False
        elif self.state == TaskState.FAILED:
            return None

        try:
            self.state = TaskState.RUNNING
            self.result = self.func(*self.args, **self.kwargs)
            self.state = TaskState.COMPLETED
            return True
        except:
            self.state = TaskState.FAILED
            return None

    def wait_result(self, timeout: float = 3.0):
        while True:
            with self._cond:
                self._cond.wait(timeout)

            if self.state in [TaskState.CANCELLED, TaskState.FAILED]:
                return None
            if self.state == TaskState.COMPLETED:
                return self.result


# this is the parent object, the access to the queue is through the Singleton below
class _TaskQueue(Queue):
    def __init__(
        self,
        *args,
        num_workers: int = 1,
        max_jobs: int = 5,
        use_log: bool = False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self._use_logger = use_log
        self._num_workers = num_workers
        self._max_jobs = max_jobs
        self._workers = []
        self._curr_id = 0
        self.start_workers()
        atexit.register(self.cancel_all_tasks)

    @property
    def new_id(self):
        self._curr_id += 1
        return self._curr_id

    @property
    def max_jobs(self):
        return self._max_jobs

    @max_jobs.setter
    def max_jobs(self, value: int):
        self._max_jobs = value

    def snapshot(self):
        with self.mutex:
            return list(self.queue)

    def add_task(self, task: Task):
        if self.qsize() >= self.max_jobs:
            return False
        else:
            self.put(task)
            return True

    def create_and_add_task(
        self,
        func: Callable,
        task_owner: discord.Member,
        args: List = [],
        kwargs: Dict = {},
    ) -> Task:
        task = Task(
            func, task_owner=task_owner, task_id=self.new_id, args=args, kwargs=kwargs
        )
        ok = self.add_task(task)
        if ok:
            return task
        else:
            return None

    def cancel_user_tasks(self, task_owner: discord.Member) -> int:
        q = self.snapshot()
        count = 0
        for task in q:
            task = cast(Task, task)
            if task.task_owner == task_owner and task.cancel():
                count += 1

        return count

    def cancel_all_tasks(self):
        return sum([int(task.cancel()) for task in self.snapshot()])

    def start_workers(self):
        for _ in range(self._num_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self._workers.append(worker)

    def _worker(self):
        while True:
            task: Task = self.get()
            res = task.run()
            if res and self._use_logger:
                self.logger.info(f"Task {task!r} completed successfully.")
            elif self._use_logger:
                self.logger.error(f"Task {task!r} failed.")

            self.task_done()


# Singleton queue object;
# currently defined to only 1 worker, since we have 1 api
# if we have multiple apis, we can increase the number of workers, but then
#  the tasks must be divided among the workers
TaskQueue = _TaskQueue(num_workers=1, max_jobs=Settings.server.max_jobs)
