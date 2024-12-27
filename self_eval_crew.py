from crewai.flow.flow import Flow, listen, start, router
from crewai import Agent, Task, Crew
from pydantic import BaseModel
import json
import yaml
import logging
from logging.handlers import RotatingFileHandler
import logging
import os
from typing import Optional, Dict, Any, List, TypedDict
from file_manager import FileManager
from agent_manager import AgentManager
from task_manager import TaskManager
from result_formatter import result_formatter

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('logs/self_eval.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


class ResearchItem(TypedDict):
    item: str
    desc: str

class ResearchResults(BaseModel):
  results: Dict[str, Any]

class EngineeredPrompt(BaseModel):
    prompt: str = ""
    prompt_change_rationale: str = ""

class AnalysisReviewState(BaseModel):
    counter: int = 0
    prompt: str = ""
    prompt_change_rationale: str = ""
    research: str = ""
    success_flag: bool = False
    feedback: str = ""

class SmartResearcher:
    def __init__(self, config_name: Optional[str] = None):
        logger.info("create SmartResearcher class")
        self.file_manager = FileManager()
        self.agent_manager = AgentManager({})
        self.task_manager = TaskManager(self.agent_manager)
        self.crew_cache = {}  # Dictionary to store initialized crews
        self.crews_loaded = False  # Flag to track if crews are loaded
        self.crews_data = None  # Store crews data when needed
        
        # Load smart research configuration
        self._load_smart_research_config()
        
        # Set config but don't initialize crews yet
        self.current_config = None
        if config_name:
            logger.info(f"Initializing SmartResearcher with config: {config_name}")
            self.current_config = self._get_config_by_name(config_name)
            if not self.current_config:
                logger.error(f"Configuration '{config_name}' not found")
                raise ValueError(f"Configuration '{config_name}' not found in smart_research.yaml")
    
    def _load_smart_research_config(self):
        """Load smart research configuration with error handling"""
        logger.info("_load_smart_research_config")
        try:
            with open('config/smart_research.yaml', 'r') as f:
                self.smart_research = yaml.safe_load(f) or {'configs': []}
            logger.debug("Successfully loaded smart research configuration")
        except Exception as e:
            logger.error(f"Error loading smart research config: {str(e)}")
            self.smart_research = {'configs': []}

    def _get_config_by_name(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration by name with logging"""
        return next(
            (cfg for cfg in self.smart_research['configs'] if cfg['name'] == config_name),
            None
        )

    def _load_crews_if_needed(self):
        """Lazy load crews data only when needed"""
        if not self.crews_loaded:
            logger.debug("Loading crews data")
            try:
                self.crews_data = self.file_manager.load_crews()
                self.crews_loaded = True
                logger.info(f"Successfully loaded {len(self.crews_data)} crews")
            except Exception as e:
                logger.error(f"Error loading crews: {str(e)}")
                self.crews_data = []

    def _get_crew(self, crew_type: str) -> Optional[Crew]:
        """Get crew with lazy loading and enhanced error handling"""
        if not self.current_config:
            logger.error("No configuration set")
            return None
            
        crew_name = self.current_config.get(f'{crew_type}_crew')
        if not crew_name:
            logger.error(f"No crew name found for type: {crew_type}")
            return None
            
        # Check cache first
        cache_key = f"{crew_type}_{crew_name}"
        if cache_key in self.crew_cache:
            logger.debug(f"Retrieved {crew_type} crew from cache: {crew_name}")
            return self.crew_cache[cache_key]
            
        # Create new crew if not in cache
        logger.info(f"Creating new {crew_type} crew: {crew_name}")
        crew = self._get_crew_by_name(crew_name)
        if crew:
            self.crew_cache[cache_key] = crew
            logger.debug(f"Cached {crew_type} crew: {crew_name}")
        return crew

    def _get_crew_by_name(self, crew_name: str) -> Optional[Crew]:
        """Get crew by name with lazy loading and enhanced logging"""
        self._load_crews_if_needed()
        
        crew_data = next(
            (crew['Crew'] for crew in self.crews_data if crew['Crew']['name'] == crew_name),
            None
        )
        
        if not crew_data:
            logger.error(f"No crew data found for name: {crew_name}")
            return None

        try:
            # Create agents with logging
            logger.debug(f"Creating agents for crew: {crew_name}")
            agents = []
            for agent_name in crew_data['agents']:
                agent = self.agent_manager.create_crewai_agent(agent_name)
                if agent:
                    agents.append(agent)
                    logger.debug(f"Created agent: {agent_name}")
                else:
                    logger.warning(f"Failed to create agent: {agent_name}")

            # Create tasks with logging
            logger.debug(f"Creating tasks for crew: {crew_name}")
            tasks = []
            for task_name in crew_data['tasks']:
                task = self.task_manager.create_crewai_task(task_name)
                if task:
                    tasks.append(task)
                    logger.debug(f"Created task: {task_name}")
                else:
                    logger.warning(f"Failed to create task: {task_name}")

            if not agents:
                logger.error(f"No valid agents created for crew: {crew_name}")
                return None
                
            if not tasks:
                logger.error(f"No valid tasks created for crew: {crew_name}")
                return None

            crew = Crew(agents=agents, tasks=tasks, verbose=True)
            logger.info(f"Successfully created crew: {crew_name}")
            return crew
            
        except Exception as e:
            logger.error(f"Error creating crew {crew_name}: {str(e)}")
            return None

    def cleanup_cache(self):
        """Clean up the crew cache"""
        logger.info("Cleaning up crew cache")
        self.crew_cache.clear()
        self.crews_loaded = False
        self.crews_data = None

    @property
    def prompt_engineer_crew(self) -> Optional[Crew]:
        return self._get_crew('prompt_engineer')

    @property
    def research_crew(self) -> Optional[Crew]:
        return self._get_crew('research')

    @property
    def research_review_crew(self) -> Optional[Crew]:
        return self._get_crew('research_review')

    @staticmethod
    def get_available_crews() -> List[str]:
        """Get list of available research crews from crews.yaml"""
        file_manager = FileManager()
        crews_data = file_manager.load_crews()
        return [crew['Crew']['name'] for crew in crews_data]

class AnalysisResearchFlow(Flow[AnalysisReviewState]):
    def __init__(self):
        super().__init__()
        self._state = AnalysisReviewState()
        self.prompt_engineering_crew = None
        self.research_crew = None
        self.research_review_crew = None

    @property
    def state(self) -> AnalysisReviewState:
        return self._state

    @state.setter
    def state(self, value: AnalysisReviewState):
        self._state = value

    def initialize_crews(self, researcher: SmartResearcher):
        self.prompt_engineering_crew = researcher.prompt_engineer_crew
        self.research_crew = researcher.research_crew
        self.research_review_crew = researcher.research_review_crew

    @start("retry")
    def start_method(self):
        logger.info("Starting the structured flow")
        if self.state.feedback:
            logger.info(f"Previous feedback: {self.state.feedback}")
            prompt_engineering_inputs = {
                "prompt": self.state.prompt,
                "feedback": self.state.feedback
            }
            self.state.counter += 1
            if self.prompt_engineering_crew:
                result = self.prompt_engineering_crew.kickoff(inputs=prompt_engineering_inputs)
                logger.debug(f"Prompt engineering result: {result}")
                pydantic_result = result.pydantic
                logger.debug(f"Prompt engineering pydantic result: {pydantic_result}")
                if pydantic_result and hasattr(pydantic_result, 'prompt'):
                    self.state.prompt = pydantic_result.prompt
                else:
                    self.state.prompt = str(prompt)
                self.state.prompt_change_rationale = pydantic_result.prompt_change_rationale
        logger.info("get input values")
        # Get inputs if they exist
        inputs = {}
        if os.path.exists('config/inputs.json'):
            with open('config/inputs.json', 'r') as f:
                inputs = json.load(f)
    
        logger.info("read input json")
        inputs["prompt"]=self.state.prompt
        logger.debug(f"Inputs: {inputs} for research")
        self.state.counter += 1
        try:
            if self.research_crew:
                logger.debug(f"Running research with prompt: {self.state.prompt}")
                result = self.research_crew.kickoff(inputs=inputs)
                logger.debug(f"research_crew Result: {result}")
                pydantic_result = result.pydantic
                if pydantic_result and hasattr(pydantic_result, 'research'):
                    self.state.research = pydantic_result.research
                else:
                    self.state.research = str(result)
            else:
                raise ValueError("Research crew not initialized")
        except Exception as e:
            logger.error(f"Error in research: {str(e)}")
            self.state.research = f"Error performing research: {str(e)}"
            return "max_retry_exceeded"

    @router(start_method)
    def second_method(self):
        logger.info("Running the second method")
        if self.state.counter > 3:
            logger.info("Max retries reached, moving to next step")
            return "max_retry_exceeded"
        
        inputs = {"research": self.state.research}
        self.state.counter += 1
        try:
            if self.research_review_crew:
                result = self.research_review_crew.kickoff(inputs=inputs)
                pydantic_result = result.pydantic
                logger.debug(f"research_review_crew Result: {result}")
                logger.debug("pydantic_result: ", pydantic_result)
                if pydantic_result and hasattr(pydantic_result, 'feedback'):
                    self.state.feedback = pydantic_result.feedback
                    self.state.success_flag = getattr(pydantic_result, 'success_flag', False)
                else:
                    logger.debug("No feedback or success_flag found in pydantic_result")
                    self.state.feedback = str(result)
                    self.state.success_flag = False
                if self.state.success_flag:
                    return "success"
                return "retry"
            else:
                raise ValueError("Research review crew not initialized")
        except Exception as e:
            logger.error(f"Error in review: {str(e)}")
            return "max_retry_exceeded"

    @listen("success")
    def third_method(self) -> str:
        logger.info("Research successfully completed")
        return self.state.research

    @listen("max_retry_exceeded")
    def max_retry_exceeded_exit(self) -> str:
        logger.info("Max retry count exceeded")
        return self.state.research if self.state.research else '{"result":"Research could not be completed"}'

class self_eval_crew(SmartResearcher):
    def __init__(self, config_name: Optional[str] = None):
        super().__init__(config_name)
        self.flow = AnalysisResearchFlow()
        self.flow.initialize_crews(self)

 

    def run_research(self, prompt: str) -> str:
        try:
            logger.info(f"Running research for {prompt}")
            self.flow.state.prompt = prompt
            result= self.flow.kickoff()
            #result=self.run_research_wrapper(prompt)
            logger.info(f'self eval result{result}')

            try:
                formatted_result = result_formatter(result)
                logger.info("Successfully formatted result using formatting agent")
                return formatted_result if formatted_result else "foo"
            except Exception as e:
                logger.error(f"Error formatting result: {str(e)}")
                logger.warning("Using raw result due to formatting error")
                    
            return result if result else "something weird"
            
        except Exception as e:
            logger.error(f"Error in run_research: {str(e)}")
            return f"Error executing research: {str(e)}"
