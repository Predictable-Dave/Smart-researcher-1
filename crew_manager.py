import logging
import yaml
import json
import os
from typing import Optional, Dict, Any, List
from crewai import Crew
#from collections.abc import Iterable

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('logs/crew_manager.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


class CrewManager:
    def __init__(self, agent_manager, task_manager, inputs):
        #self.logger = logging.getLogger(__name__)
        self.agent_manager = agent_manager
        self.task_manager = task_manager
        self.inputs = inputs
        self.last_execution_results = {}
        self.crew_cache = {}
        
        # Load crews from file
        try:
            with open('config/crews.yaml', 'r') as f:
                self.crews = yaml.safe_load(f) or []
        except FileNotFoundError:
            with open('config/crews.yaml', 'w') as f:
                yaml.dump([], f)
            self.crews = []
        except Exception as e:
            logger.error(f"Error loading crews: {str(e)}")
            self.crews = []

    def process_json_output(self, raw_output: Any) -> Dict[str, Any]:
        try:
            # If it's already a dict, return it directly
            if isinstance(raw_output, dict):
                return raw_output

            # If it's a string, try to parse it as JSON
            if isinstance(raw_output, str):
                # Check if it's HTML content
                if raw_output.strip().startswith('<!DOCTYPE') or raw_output.strip().startswith('<html'):
                    logger.error("Received HTML content instead of JSON")
                    return {'error': 'Invalid response format received'}

                # Remove markdown code blocks if present
                cleaned_str = raw_output.strip('`').replace('```json\n', '').replace('```', '')
                try:
                    return json.loads(cleaned_str)
                except json.JSONDecodeError:
                    return {'data': cleaned_str}

            # Handle pydantic models
            if hasattr(raw_output, 'dict'):
                return raw_output.dict()

            # For any other type, wrap it in a dict
            return {'data': str(raw_output)}
        except Exception as e:
            logger.error(f"Error processing JSON output: {str(e)}")
            return {'error': f'Failed to process output: {str(e)}'}

    def execute_crew(self, crew_name: str) -> Dict[str, Any]:
        """Execute a crew and return results"""
        if not crew_name:
            return {'error': 'No crew name provided'}
            
        try:
            crew = self.create_crewai_crew(crew_name)
            if not crew:
                return {'error': f'Could not create crew: {crew_name}'}
                
                    
            # Execute crew
            result = crew.kickoff(inputs=self.inputs)
            if not result:
                return {'error': 'No result from crew execution'}
                
            # Store and return result
            self.last_execution_results[crew_name] = result
            if result.json_dict:
                return {'result':result.json_dict}
            if result.pydantic:
                logger.debug(f"pydantic result: {result.pydantic}")
                return {'result':result.pydantic.results}
            logger.debug(f"result: {result}")
            return {'result': result.raw}
            
        except Exception as e:
            logger.error(f'Error executing crew {crew_name}: {str(e)}')
            return {'error': str(e)}

    def create_crewai_crew(self, crew_name: str) -> Optional[Crew]:
        # Check cache first
        if crew_name in self.crew_cache:
            logger.debug(f"Returning cached crew for {crew_name}")
            return self.crew_cache[crew_name]

        logger.debug(f"Creating crew with name: {crew_name}")
        crew_data = self.get_crewai_crew_by_name(crew_name)
        if crew_data:
            logger.debug(f"Found crew data: {crew_data}")
            
            # Create agents with proper error handling and type checking
            agents = []
            for agent_name in crew_data['agents']:
                agent = self.agent_manager.create_crewai_agent(agent_name)
                if agent is None:
                    logger.error(f"Failed to create agent {agent_name} for crew {crew_name}")
                    continue
                agents.append(agent)
            
            # Create tasks with proper error handling and type checking
            tasks = []
            for task_name in crew_data['tasks']:
                task = self.task_manager.create_crewai_task(task_name)
                if task is None:
                    logger.error(f"Failed to create task {task_name} for crew {crew_name}")
                    continue
                tasks.append(task)
            
            if not agents:
                logger.error(f"No valid agents created for crew {crew_name}")
                return None
                
            if not tasks:
                logger.error(f"No valid tasks created for crew {crew_name}")
                return None
                
            try:
                crew_kwargs = {
                    'agents': agents,
                    'tasks': tasks,
                    'verbose': True
                }
                
                crew = Crew(**crew_kwargs)
                # Store in cache
                self.crew_cache[crew_name] = crew
                logger.debug(f"Successfully created and cached crew object for {crew_name}")
                return crew
            except Exception as e:
                logger.error(f"Error creating crew object: {str(e)}")
                return None
        else:
            logger.error(f"No crew data found for name: {crew_name}")
            return None

    def get_crewai_crew_by_name(self, crew_name: str) -> Optional[Dict[str, Any]]:
        """Get crew configuration by name with enhanced error handling"""
        try:
            for crew in self.crews:
                if crew and isinstance(crew, dict) and 'Crew' in crew:
                    if crew['Crew'].get('name') == crew_name:
                        logger.info(f"Found crew configuration for: {crew_name}")
                        return crew['Crew']
            
            logger.error(f"No crew found with name: {crew_name}")
            logger.debug(f"Available crews: {[c.get('Crew', {}).get('name') for c in self.crews if c]}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving crew {crew_name}: {str(e)}")
            return None

    def create_crew(self, crew_data: Dict[str, Any]) -> bool:
        try:
            self.crews.append({'Crew': crew_data})
            return True
        except Exception as e:
            logger.error(f"Error creating crew: {str(e)}")
            return False

    def update_crew(self, index: int, crew_data: Dict[str, Any]) -> bool:
        if 0 <= index < len(self.crews):
            try:
                # Clear cache entry if it exists
                crew_name = self.crews[index]['Crew'].get('name')
                if crew_name and crew_name in self.crew_cache:
                    del self.crew_cache[crew_name]
                    
                self.crews[index]['Crew'] = crew_data
                return True
            except Exception as e:
                logger.error(f"Error updating crew: {str(e)}")
                return False
        return False

    def delete_crew(self, index: int) -> bool:
        if 0 <= index < len(self.crews):
            try:
                # Clear cache entry if it exists
                crew_name = self.crews[index]['Crew'].get('name')
                if crew_name and crew_name in self.crew_cache:
                    del self.crew_cache[crew_name]
                    
                del self.crews[index]
                return True
            except Exception as e:
                logger.error(f"Error deleting crew: {str(e)}")
                return False
        return False
