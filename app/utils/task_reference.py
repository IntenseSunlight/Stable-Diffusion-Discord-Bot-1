import asyncio
import weakref

__all__ = ["TaskRef"]


class _TaskReference:
    def __init__(self):
        self._data = weakref.WeakValueDictionary()

    @property
    def data(self):
        return self._data

    def add_task(self, task: asyncio.Task):
        self._data[task.get_name()] = task
        return task

    def get_tasks(self):
        return list(self._data.values())

    def cancel(self, task_name: str):
        task: asyncio.Task = self._data.get(task_name, None)
        if task is not None:
            task.cancel()

    def cancel_all(self):
        for task in self.get_tasks():
            task.cancel()


TaskRef = _TaskReference()
