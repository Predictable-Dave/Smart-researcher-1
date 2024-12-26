import os
import logging
from logging.handlers import RotatingFileHandler
import yaml
import json
from typing import List, Dict, Any

class FileManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

    def setup_logging(self):
        os.makedirs('logs', exist_ok=True)
        log_file = 'logs/app_state.log'
        file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.DEBUG)

    def load_agents(self) -> List[Dict[str, Any]]:
        try:
            with open('config/agents.yaml', 'r') as file:
                return yaml.safe_load(file) or []
        except FileNotFoundError:
            self.logger.warning('config/agents.yaml not found. Creating an empty file.')
            os.makedirs('config', exist_ok=True)
            with open('config/agents.yaml', 'w') as file:
                yaml.dump([], file)
            return []

    def load_tasks(self) -> List[Dict[str, Any]]:
        try:
            with open('config/tasks.yaml', 'r') as file:
                return yaml.safe_load(file) or []
        except FileNotFoundError:
            self.logger.warning('config/tasks.yaml not found. Creating an empty file.')
            os.makedirs('config', exist_ok=True)
            with open('config/tasks.yaml', 'w') as file:
                yaml.dump([], file)
            return []

    def load_crews(self) -> List[Dict[str, Any]]:
        try:
            with open('config/crews.yaml', 'r') as file:
                return yaml.safe_load(file) or []
        except FileNotFoundError:
            self.logger.warning('config/crews.yaml not found. Creating an empty file.')
            os.makedirs('config', exist_ok=True)
            with open('config/crews.yaml', 'w') as file:
                yaml.dump([], file)
            return []

    def load_inputs(self) -> Dict[str, Any]:
        try:
            with open('config/inputs.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            self.logger.warning('config/inputs.json not found. Creating an empty file.')
            os.makedirs('config', exist_ok=True)
            with open('config/inputs.json', 'w') as file:
                json.dump({}, file)
            return {}

    def save_agents(self, agents: List[Dict[str, Any]]) -> bool:
        try:
            self.logger.debug("Saving agents to config/agents.yaml")
            with open('config/agents.yaml', 'w') as file:
                yaml.dump(agents, file)
            self.logger.debug("Agents saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error saving agents: {str(e)}")
            return False

    def save_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        try:
            self.logger.debug("Saving tasks to config/tasks.yaml")
            with open('config/tasks.yaml', 'w') as file:
                yaml.dump(tasks, file)
            self.logger.debug("Tasks saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error saving tasks: {str(e)}")
            return False

    def save_crews(self, crews: List[Dict[str, Any]]) -> bool:
        try:
            self.logger.debug("Saving crews to config/crews.yaml")
            with open('config/crews.yaml', 'w') as file:
                yaml.dump(crews, file)
            self.logger.debug("Crews saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error saving crews: {str(e)}")
            return False

    def save_inputs(self, inputs: Dict[str, Any]) -> bool:
        try:
            self.logger.debug("Saving inputs to config/inputs.json")
            with open('config/inputs.json', 'w') as file:
                json.dump(inputs, file)
            self.logger.debug("Inputs saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error saving inputs: {str(e)}")
            return False
