import os
import logging
from logging.handlers import RotatingFileHandler
import yaml
import json
from typing import List, Optional, Dict, Any, Sequence
from collections.abc import Iterable
from crewai import Agent, Task, Crew
from file_manager import FileManager
from agent_manager import AgentManager
from task_manager import TaskManager
from crew_manager import CrewManager
#required 
from tools.search_tools import SearchTools
from tools.semantic_search import ExaSearchTool
from tools.calculator_tools import CalculatorTool
from tools.scraper_tools import WebScrappingTools
from tools.excel_rag_tool import ExcelRagTool
from tools.cached_result_tool import DummyTool
from tools.graph_rag_tool import GraphRagTool
from db_utils import set_up_db

# Define tools dictionary
tools_dict = {
    "ExaSearchTool": ExaSearchTool.search_and_get_contents_tool,
    "Search Tavily": SearchTools.TavilySearchTool,
    "Search Internet": SearchTools.search_internet_with_google,
    "Search News": SearchTools.search_news_with_google,
    "Scrape Company": WebScrappingTools.extract_company_overview,
    "Scrape Data Centre": WebScrappingTools.extract_data_centre_key_facts,
    "Calculator": CalculatorTool.evaluate,
    "DC Excel RAG": ExcelRagTool.query_data_centre_src,
    "Excel RAG": ExcelRagTool.query_excel_src,
    "Graph RAG": GraphRagTool.get_PDF_insight,
    "Dummy Tool": DummyTool.get_dummy_result,
    "Smart Excel RAG":ExcelRagTool.query_excel_rag
}

class CrewEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (Agent, Task, Crew)):
            return str(o)
        return super().default(o)

class AppState:
    def __init__(self, tools: Dict[str, Any]=tools_dict):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        self.logger.info("Initializing AppState")
        
        # Ensure config directory exists
        try:
            os.makedirs('config', exist_ok=True)
            self.logger.debug("Config directory ensured")
        except Exception as e:
            self.logger.error(f"Failed to create config directory: {str(e)}")
            raise
        
        # Initialize basic components
        try:
            self.logger.debug("Initializing FileManager")
            self.file_manager = FileManager()
            self.tools = tools if tools else {}
            self.last_execution_results = {}
            self.logger.debug(f"Available tools: {list(self.tools.keys())}")
        except Exception as e:
            self.logger.error(f"Failed to initialize basic components: {str(e)}")
            raise
        
        # Create empty config files if they don't exist
        try:
            self.logger.debug("Ensuring config files exist")
            self._ensure_config_files_exist()
        except Exception as e:
            self.logger.error(f"Failed to ensure config files: {str(e)}")
            raise
        # create cache database 
        set_up_db()
        self.inputs = self._load_data('inputs')
        try:
            # Initialize managers
            self.logger.debug("Initializing managers")
            try:
                self.logger.debug("Initializing AgentManager")
                self.agent_manager = AgentManager(self.tools)
                self.logger.debug("Initializing TaskManager")
                self.task_manager = TaskManager(self.agent_manager)
                self.logger.debug("Initializing CrewManager")
                self.crew_manager = CrewManager(self.agent_manager, 
                                                self.task_manager,self.inputs)
                self.logger.debug("All managers initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize managers: {str(e)}", exc_info=True)
                raise
            
            # Load data from files with error handling
            self.logger.debug("Loading data from config files")
            self.agents = self._load_data('agents')
            self.tasks = self._load_data('tasks')
            self.crews = self._load_data('crews')

            
            # Set up managers with loaded data
            self.logger.debug("Setting up managers with loaded data")
            self.agent_manager.agents = self.agents
            self.task_manager.tasks = self.tasks
            self.crew_manager.crews = self.crews
            
            # Initialize smart research crew
            self.logger.debug("Initializing smart research crew")
            self._init_smart_research()
            
            self.logger.info("AppState initialization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during AppState initialization: {str(e)}", exc_info=True)
            # Initialize empty data structures as fallback
            self.agents = []
            self.tasks = []
            self.crews = []
            self.inputs = {}
            raise
    
    def _ensure_config_files_exist(self):
        """Ensure all required config files exist"""
        config_files = {
            'agents.yaml': [],
            'tasks.yaml': [],
            'crews.yaml': [],
            'inputs.json': {},
            'smart_research.yaml': {'configs': []}
        }
        
        for filename, default_content in config_files.items():
            filepath = os.path.join('config', filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    if filename.endswith('.json'):
                        json.dump(default_content, f, indent=2)
                    else:
                        yaml.dump(default_content, f)
    
    def _load_data(self, data_type: str) -> Any:
        """Load data from config files with error handling"""
        try:
            if data_type == 'inputs':
                with open(f'config/inputs.json', 'r') as f:
                    return json.load(f)
            else:
                with open(f'config/{data_type}.yaml', 'r') as f:
                    return yaml.safe_load(f) or []
        except Exception as e:
            self.logger.error(f"Error loading {data_type}: {str(e)}")
            return [] if data_type != 'inputs' else {}
    
    def _init_smart_research(self):
        """Initialize smart research configuration"""
        try:
            with open('config/smart_research.yaml', 'r') as f:
                smart_research = yaml.safe_load(f) or {'configs': []}
                default_config = smart_research['configs'][0] if smart_research['configs'] else None
        except Exception as e:
            self.logger.error(f"Error loading default configuration: {str(e)}")

    def setup_logging(self):
        os.makedirs('logs', exist_ok=True)
        log_file = 'logs/app_state.log'
        file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.DEBUG)

    def get_last_execution_result(self, name: str) -> Optional[Dict[str, Any]]:
        return self.last_execution_results.get(name)
