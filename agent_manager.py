import logging
import yaml
from typing import Optional, Dict, Any, List, Union, Type
from crewai import Agent
from langchain.tools import BaseTool
import inspect
import asyncio
from pydantic import BaseModel, Field, create_model
from langchain.tools import StructuredTool

class AgentManager:
    def __init__(self, tools: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.tools = tools
        self.agents = []
        self.agent_cache = {}  # Cache for created agents

    def create_crewai_agent(self, agent_name: str) -> Optional[Agent]:
        # First check if agent already exists in loaded agents
        agent_data = self.get_agent_by_name(agent_name)
        
        if not agent_data:
            # Agent not found in current agents, try to load from agents.yaml
            try:
                with open('config/agents.yaml', 'r') as f:
                    all_agents = yaml.safe_load(f) or []
                    agent_data = next((agent['Agent'] for agent in all_agents 
                                     if agent['Agent']['name'] == agent_name), None)
                    if agent_data:
                        # Add to current agents list
                        self.agents.append({'Agent': agent_data})
            except Exception as e:
                self.logger.error(f"Error loading agent {agent_name}: {str(e)}")
                return None
                
        if agent_data:
            try:
                agent_kwargs = {
                    'name': agent_data['name'],
                    'role': agent_data['role'],
                    'goal': agent_data['goal'],
                    'backstory': agent_data['backstory'],
                    'verbose': True,
                    'allow_delegation': agent_data.get('delegate', False)
                }

                if 'tools' in agent_data and agent_data['tools']:
                    tools = []
                    for tool_name in agent_data['tools']:
                        if tool_name in self.tools:
                            tool = self.tools[tool_name]
                            #converted_tool = self._convert_structured_tool(tool, tool_name)
                            #if converted_tool:
                            #    tools.append(converted_tool)
                            #    self.logger.debug(f"Successfully converted tool {tool_name}")
                            #else:
                            #    self.logger.warning(f"Failed to convert tool {tool_name}")
                            tools.append(tool)
                                
                    if tools:
                        agent_kwargs['tools'] = tools
                        
                return Agent(**agent_kwargs)
            except Exception as e:
                self.logger.error(f"Error creating agent {agent_name}: {str(e)}")
                return None
        
        self.logger.error(f"No agent data found for {agent_name}")
        return None

    def _convert_structured_tool(self, tool: Union[StructuredTool, BaseTool], tool_name: str) -> Optional[BaseTool]:
        """Convert any tool type to a proper BaseTool instance with enhanced validation and schema handling"""
        print(f"Converting tool {tool} and {tool_name} to BaseTool")
        
        try:
            # If it's already a BaseTool instance (not StructuredTool), return it directly
            if isinstance(tool, BaseTool) and not isinstance(tool, StructuredTool):
                return tool

            # For StructuredTool, create a proper BaseTool wrapper
            if isinstance(tool, StructuredTool):
                func = tool._run
                schema = None
                if hasattr(tool, 'args_schema'):
                    schema = tool.args_schema
                
                # Create dynamic schema if needed
                if schema is None and hasattr(tool, '_function'):
                    sig = inspect.signature(tool._function)
                    fields = {}
                    for param_name, param in sig.parameters.items():
                        if param.annotation != inspect.Parameter.empty:
                            fields[param_name] = (param.annotation, Field(description=f"Parameter {param_name}"))
                    if fields:
                        schema = create_model('DynamicSchema', **fields)

                class WrappedTool(BaseTool):
                    name: str = Field(default=tool.name)
                    description: str = Field(default=tool.description)
                    return_direct: bool = Field(default=False)
                    args_schema: Optional[Type[BaseModel]] = schema

                    def _run(self, query: Any) -> Any:
                        try:
                            if isinstance(query, dict) and self.args_schema:
                                return func(**query)
                            return func(query)
                        except Exception as e:
                            self.logger.error(f"Error in tool execution: {str(e)}")
                            return f"Error executing {self.name}: {str(e)}"

                    async def _arun(self, query: Any) -> Any:
                        try:
                            if hasattr(tool, '_arun'):
                                if isinstance(query, dict) and self.args_schema:
                                    return await tool._arun(**query)
                                return await tool._arun(query)
                            return await asyncio.to_thread(self._run, query)
                        except Exception as e:
                            self.logger.error(f"Error in async tool execution: {str(e)}")
                            return f"Error executing {self.name} asynchronously: {str(e)}"

                return WrappedTool()

            # For function-based tools, create a BaseTool wrapper
            func = tool if callable(tool) else getattr(tool, '_run', None)
            if not func:
                self.logger.error(f"No callable function found for tool {tool_name}")
                return None

            class FunctionBasedTool(BaseTool):
                name: str = Field(default=getattr(tool, 'name', tool_name))
                description: str = Field(default=getattr(tool, 'description', f"Tool for {tool_name}"))
                return_direct: bool = Field(default=False)

                def _run(self, query: Any) -> Any:
                    try:
                        return func(query)
                    except Exception as e:
                        self.logger.error(f"Error in tool execution: {str(e)}")
                        return f"Error executing {self.name}: {str(e)}"

                async def _arun(self, query: Any) -> Any:
                    return await asyncio.to_thread(self._run, query)

            return FunctionBasedTool()

            

        except Exception as e:
            self.logger.error(f"Error converting tool {tool_name}: {str(e)}")
            return None

    def get_agent_by_name(self, agent_name: str) -> Optional[Dict[str, Any]]:
        for agent in self.agents:
            if agent['Agent']['name'] == agent_name:
                return agent['Agent']
        return None

    def create_agent(self, agent_data: Dict[str, Any]) -> bool:
        try:
            self.agents.append({'Agent': agent_data})
            return True
        except Exception as e:
            self.logger.error(f"Error creating agent: {str(e)}")
            return False

    def update_agent(self, index: int, agent_data: Dict[str, Any]) -> bool:
        if 0 <= index < len(self.agents):
            try:
                # Clear cache entry if it exists
                agent_name = self.agents[index]['Agent'].get('name')
                if agent_name and agent_name in self.agent_cache:
                    del self.agent_cache[agent_name]
                    
                self.agents[index]['Agent'] = agent_data
                return True
            except Exception as e:
                self.logger.error(f"Error updating agent: {str(e)}")
                return False
        return False

    def delete_agent(self, index: int) -> bool:
        if 0 <= index < len(self.agents):
            try:
                # Clear cache entry if it exists
                agent_name = self.agents[index]['Agent'].get('name')
                if agent_name and agent_name in self.agent_cache:
                    del self.agent_cache[agent_name]
                    
                del self.agents[index]
                return True
            except Exception as e:
                self.logger.error(f"Error deleting agent: {str(e)}")
                return False
        return False
