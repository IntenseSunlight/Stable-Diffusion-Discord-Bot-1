import unittest
from time import sleep
from app.utils.task_queue import TaskQueue, Task, TaskState


def long_task(delay: int = 5):
    sleep(delay)
    return delay


def bad_task():
    raise ValueError("bad task")


class TestTaskQueue(unittest.TestCase):
    def test_task(self):
        t = Task(long_task, task_owner="me", delay=0.5)
        t.run()
        self.assertEqual(t.state, TaskState.COMPLETED)

    def test_task_fail(self):
        t = Task(bad_task, task_owner="me")
        t.run()
        self.assertEqual(t.state, TaskState.FAILED)

    def test_queue_add_task(self):
        TaskQueue._use_logger = True
        t = Task(long_task, task_owner="me", delay=3)
        TaskQueue.add_task(t)
        TaskQueue.join()
        self.assertEqual(t.state, TaskState.COMPLETED)
        self.assertEqual(t.result, 3)

    def test_queue_create_and_add_task(self):
        TaskQueue._use_logger = True
        t = TaskQueue.create_and_add_task(long_task, task_owner="me", delay=3)
        TaskQueue.join()
        self.assertEqual(t.state, TaskState.COMPLETED)
        self.assertEqual(t.result, 3)

    def test_queue_cancel_task(self):
        TaskQueue._use_logger = True
        t = Task(long_task, task_owner="me", delay=3)
        TaskQueue.add_task(t)
        t.cancel()
        TaskQueue.join()
        self.assertEqual(t.state, TaskState.CANCELLED)

    def test_queue_cancel_task_running(self):
        TaskQueue._use_logger = True
        a = TaskQueue.create_and_add_task(long_task, task_owner="me", delay=3)
        b = TaskQueue.create_and_add_task(long_task, task_owner="me", delay=4)
        c = TaskQueue.create_and_add_task(long_task, task_owner="me", delay=5)
        sleep(1)
        self.assertEqual(a.state, TaskState.RUNNING)
        self.assertEqual(b.state, TaskState.PENDING)
        self.assertEqual(c.state, TaskState.PENDING)
        res = c.wait_result()
        self.assertEqual(res, 5)

    def test_add_too_many_tasks(self):
        TaskQueue._use_logger = True
        TaskQueue.max_jobs = 3
        for _ in range(4):
            t = TaskQueue.create_and_add_task(long_task, task_owner="me", delay=3)
        self.assertIsNone(t)
        self.assertEqual(TaskQueue.qsize(), 3)
        TaskQueue.join()
        self.assertEqual(TaskQueue.qsize(), 0)
