import logging
import yaml
from typing import Optional, Dict, Any, List
from crewai import Task
import importlib

class TaskManager:
    def __init__(self, agent_manager):
        self.logger = logging.getLogger(__name__)
        self.agent_manager = agent_manager
        self.tasks = []

    def _import_pydantic_class(self, class_path: str) -> Optional[Any]:
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Error importing pydantic class {class_path}: {str(e)}")
            return None

    def create_crewai_task(self, task_name: str) -> Optional[Task]:
        # First check if task exists in loaded tasks
        task_data = next((task['Task'] for task in self.tasks 
                         if task['Task']['name'] == task_name), None)
        
        if not task_data:
            # Task not found in current tasks, try to load from tasks.yaml
            try:
                with open('config/tasks.yaml', 'r') as f:
                    all_tasks = yaml.safe_load(f) or []
                    task_data = next((task['Task'] for task in all_tasks 
                                    if task['Task']['name'] == task_name), None)
                    if task_data:
                        # Add to current tasks list
                        self.tasks.append({'Task': task_data})
            except Exception as e:
                self.logger.error(f"Error loading task {task_name}: {str(e)}")
                return None
        
        if task_data:
            if not task_data.get('agent'):
                self.logger.error(f"No agent specified for task {task_name}")
                return None
                
            agent = self.agent_manager.create_crewai_agent(task_data['agent'])
            if not agent:
                self.logger.error(f"Could not create agent {task_data['agent']} for task {task_name}")
                return None
                
            task_kwargs = {
                'description': task_data['description'],
                'agent': agent,
                'json': True
            }
            
            # Handle pydantic class if specified
            if pydantic_class := task_data.get('pydantic_class'):
                pydantic_cls = self._import_pydantic_class(pydantic_class)
                if pydantic_cls:
                    task_kwargs['output_pydantic'] = pydantic_cls
            
            if 'expected_output' in task_data:
                task_kwargs['expected_output'] = task_data['expected_output']
            
            if task_data.get('tools'):
                try:
                    tools_list = []
                    if agent.tools:
                        for tool_name in task_data['tools']:
                            matching_tools = [tool for tool in agent.tools if tool.__name__ == tool_name]
                            if matching_tools:
                                tools_list.extend(matching_tools)
                    if tools_list:
                        task_kwargs['tools'] = tools_list
                except Exception as e:
                    self.logger.error(f"Error setting up tools for task {task_name}: {str(e)}")
            
            try:
                return Task(**task_kwargs)
            except Exception as e:
                self.logger.error(f"Error creating task {task_name}: {str(e)}")
                return None
                
        self.logger.error(f"No task data found for {task_name}")
        return None

    def create_task(self, task_data: Dict[str, Any]) -> bool:
        try:
            self.tasks.append({'Task': task_data})
            return True
        except Exception as e:
            self.logger.error(f"Error creating task: {str(e)}")
            return False

    def update_task(self, index: int, task_data: Dict[str, Any]) -> bool:
        if 0 <= index < len(self.tasks):
            try:
                self.tasks[index]['Task'] = task_data
                return True
            except Exception as e:
                self.logger.error(f"Error updating task: {str(e)}")
                return False
        return False

    def delete_task(self, index: int) -> bool:
        if 0 <= index < len(self.tasks):
            try:
                del self.tasks[index]
                return True
            except Exception as e:
                self.logger.error(f"Error deleting task: {str(e)}")
                return False
        return False
