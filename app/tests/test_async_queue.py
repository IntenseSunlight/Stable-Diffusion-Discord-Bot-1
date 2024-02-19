import unittest
import asyncio
from time import sleep
from app.utils.async_task_queue import Task, TaskState, _AsyncTaskQueue


# These test function are intended to be synchronous
def long_task(delay: int = 5):
    sleep(delay)
    return delay


def bad_task():
    raise ValueError("bad task")


async def async_long_task(delay: int = 5):
    await asyncio.sleep(delay)
    return delay


# Note: The following cases test individual methods of the AsyncTaskQueue
# Due to unittest's conflicting event loops working with the singleton AsyncTaskQueue,
# a seperate `AQ` instance is created for each test case.
# (the `unittest.IsolatedAsyncioTestCase` class creates a new event loop for each test case,
#  which is not the case when used with Discord ((uses a single event loop)).  Therefore
#  seperate instances of AsyncTaskQueue are required to deal with the seperate event loops).


class TestAsyncTaskQueue(unittest.IsolatedAsyncioTestCase):

    async def test_task(self):
        t = Task(long_task, task_owner="me", kwargs=dict(delay=0.5))
        await t.run()
        self.assertEqual(t.state, TaskState.COMPLETED)

    async def test_task_fail(self):
        t = Task(bad_task, task_owner="me")
        await t.run()
        self.assertEqual(t.state, TaskState.FAILED)

    def test_task_equal(self):
        t1 = Task(long_task, task_owner="me", task_id=1, kwargs=dict(delay=3))
        t2 = Task(long_task, task_owner="you", task_id=2, kwargs=dict(delay=3))
        tasks = [t1, t2]
        for t in tasks:
            if t == t2:
                self.assertEqual(t.task_owner, "you")

        self.assertNotEqual(t1, t2)

    async def test_queue_add_task(self):
        AQ = _AsyncTaskQueue()
        AQ._use_logger = True
        t = Task(long_task, task_owner="me", kwargs=dict(delay=3))
        await AQ.add_task(t)
        await AQ.join()
        self.assertEqual(t.state, TaskState.COMPLETED)
        self.assertEqual(t.result, 3)

    async def test_queue_create_and_add_task(self):
        AQ = _AsyncTaskQueue()
        AQ._use_logger = True
        t = await AQ.create_and_add_task(
            long_task, task_owner="me", kwargs=dict(delay=3)
        )
        await AQ.join()
        self.assertEqual(t.state, TaskState.COMPLETED)
        self.assertEqual(t.result, 3)

    async def test_queue_add_async_task(self):
        AQ = _AsyncTaskQueue()
        AQ._use_logger = True
        t = Task(async_long_task, task_owner="me", kwargs=dict(delay=3))
        await AQ.add_task(t)
        await AQ.join()
        self.assertEqual(t.state, TaskState.COMPLETED)
        self.assertEqual(t.result, 3)

    async def test_queue_create_and_add_async_task(self):
        AQ = _AsyncTaskQueue()
        AQ._use_logger = True
        t = await AQ.create_and_add_task(
            async_long_task, task_owner="me", kwargs=dict(delay=3)
        )
        await AQ.join()
        self.assertEqual(t.state, TaskState.COMPLETED)
        self.assertEqual(t.result, 3)

    async def test_queue_cancel_task(self):
        AQ = _AsyncTaskQueue()
        AQ._use_logger = True
        t = Task(long_task, task_owner="me", kwargs=dict(delay=3))
        await AQ.add_task(t)
        t.cancel()
        await AQ.join()
        self.assertEqual(t.state, TaskState.CANCELLED)

    async def test_queue_cancel_task_running(self):
        AQ = _AsyncTaskQueue()
        AQ._use_logger = True
        a = await AQ.create_and_add_task(
            long_task, task_owner="me", kwargs=dict(delay=3)
        )
        b = await AQ.create_and_add_task(
            long_task, task_owner="me", kwargs=dict(delay=4)
        )
        c = await AQ.create_and_add_task(
            long_task, task_owner="me", kwargs=dict(delay=5)
        )
        await asyncio.sleep(1)
        self.assertEqual(a.state, TaskState.RUNNING)
        self.assertEqual(b.state, TaskState.PENDING)
        self.assertEqual(c.state, TaskState.PENDING)
        res = await c.wait_result()
        self.assertEqual(res, 5)

    async def test_add_too_many_tasks(self):
        AQ = _AsyncTaskQueue()
        AQ._use_logger = True
        AQ.max_jobs = 3
        for _ in range(4):
            t = await AQ.create_and_add_task(
                long_task, task_owner="me", kwargs=dict(delay=3)
            )
        self.assertIsNone(t)
        self.assertEqual(AQ.qsize(), 3)
        await AQ.join()
        self.assertEqual(AQ.qsize(), 0)

    async def test_queue_cancel_user_tasks(self):
        AQ = _AsyncTaskQueue()
        AQ._use_logger = True
        AQ.max_jobs = 5
        _ = await AQ.create_and_add_task(
            long_task, task_owner="me", kwargs=dict(delay=3)
        )
        b = await AQ.create_and_add_task(
            long_task, task_owner="me", kwargs=dict(delay=4)
        )
        c = await AQ.create_and_add_task(
            long_task, task_owner="me", kwargs=dict(delay=5)
        )
        d = await AQ.create_and_add_task(
            long_task, task_owner="bob", kwargs=dict(delay=3)
        )
        AQ.cancel_user_tasks("me")
        self.assertEqual(b.state, TaskState.CANCELLED)
        self.assertEqual(c.state, TaskState.CANCELLED)
        self.assertEqual(d.state, TaskState.PENDING)
        await AQ.join()

    async def test_queue_cancel_all_tasks(self):
        AQ = _AsyncTaskQueue()
        AQ._use_logger = True
        AQ.max_jobs = 10
        for _ in range(3):
            await AQ.create_and_add_task(
                long_task, task_owner="me", kwargs=dict(delay=3)
            )

        for _ in range(3):
            await AQ.create_and_add_task(
                long_task, task_owner="bob", kwargs=dict(delay=3)
            )

        for _ in range(3):
            await AQ.create_and_add_task(
                long_task, task_owner="alice", kwargs=dict(delay=3)
            )

        await asyncio.sleep(1)  # let first task start
        n_canceled = AQ.cancel_all_tasks()
        await AQ.join()

        # first task was already started when others were canceled, so 8 tasks should be canceled
        self.assertEqual(n_canceled, 8)
