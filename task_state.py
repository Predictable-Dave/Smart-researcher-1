from enum import Enum
import yaml

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskState:
    def __init__(self):
        self.tasks = self.load_tasks()

    def load_tasks(self):
        with open('tasks.yaml', 'r') as file:
            return yaml.safe_load(file) or []

    def save_tasks(self):
        with open('tasks.yaml', 'w') as file:
            yaml.dump(self.tasks, file, default_flow_style=False)

    def create_task(self, task_data):
        new_task = {
            'Task': {
                **task_data,
                'status': TaskStatus.PENDING.value
            }
        }
        self.tasks.append(new_task)
        self.save_tasks()
        return new_task

    def update_task(self, index, task_data):
        if 0 <= index < len(self.tasks):
            self.tasks[index]['Task'].update(task_data)
            self.save_tasks()
            return True
        return False

    def update_task_status(self, task_name, new_status):
        for task in self.tasks:
            if task['Task']['name'] == task_name:
                task['Task']['status'] = new_status.value
                self.save_tasks()
                return True
        return False

    def delete_task(self, index):
        if 0 <= index < len(self.tasks):
            del self.tasks[index]
            self.save_tasks()
            return True
        return False

    def get_task(self, task_name):
        for task in self.tasks:
            if task['Task']['name'] == task_name:
                return task['Task']
        return None

    def get_all_tasks(self):
        return self.tasks

    def start_task(self, task_name):
        return self.update_task_status(task_name, TaskStatus.IN_PROGRESS)

    def complete_task(self, task_name):
        return self.update_task_status(task_name, TaskStatus.COMPLETED)

    def fail_task(self, task_name):
        return self.update_task_status(task_name, TaskStatus.FAILED)
