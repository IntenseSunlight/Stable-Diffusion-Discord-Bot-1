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

    def test_queue_cancel_user_tasks(self):
        TaskQueue._use_logger = True
        TaskQueue.max_jobs = 5
        _ = TaskQueue.create_and_add_task(long_task, task_owner="me", delay=3)
        b = TaskQueue.create_and_add_task(long_task, task_owner="me", delay=4)
        c = TaskQueue.create_and_add_task(long_task, task_owner="me", delay=5)
        d = TaskQueue.create_and_add_task(long_task, task_owner="bob", delay=3)
        TaskQueue.cancel_user_tasks("me")
        self.assertEqual(b.state, TaskState.CANCELLED)
        self.assertEqual(c.state, TaskState.CANCELLED)
        self.assertEqual(d.state, TaskState.PENDING)
        TaskQueue.join()

    def test_queue_cancel_all_tasks(self):
        TaskQueue._use_logger = True
        TaskQueue.max_jobs = 10
        for _ in range(3):
            TaskQueue.create_and_add_task(long_task, task_owner="me", delay=3)

        for _ in range(3):
            TaskQueue.create_and_add_task(long_task, task_owner="bob", delay=3)

        for _ in range(3):
            TaskQueue.create_and_add_task(long_task, task_owner="alice", delay=3)

        sleep(1)  # let first task start
        n_canceled = TaskQueue.cancel_all_tasks()
        TaskQueue.join()

        # first task was already started when others were canceled, so 8 tasks should be canceled
        self.assertEqual(n_canceled, 8)
