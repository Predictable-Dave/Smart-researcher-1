from flask import render_template, request, redirect, url_for, flash
from flask_wtf.csrf import generate_csrf
from flask_wtf.csrf import CSRFError
import logging
import json
import pandas as pd
import yaml
# Import required packages with error handling
try:
    import pandas as pd
except ImportError:
    pd = None  # Handle case where pandas is not available
#from task_outputs import pydantic_class_dict,
from task_outputs import enhanced_pydantic_classes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def manage_tasks_helper(app_state):
  """Handle task management operations"""
  logger.info("Accessing manage_tasks route")
  tasks = []
  agents = []
  available_tools = []


  if request.method == 'POST':
      try:
          # Load current tasks
          with open('config/tasks.yaml', 'r') as f:
              tasks = yaml.safe_load(f) or []

          action = request.form.get('action')
          if action in ['add', 'edit']:
              task_data = {
                  'name': request.form.get('name'),
                  'description': request.form.get('description'),
                  'expected_output': request.form.get('expected_output'),
                  'agent': request.form.get('agent'),
                  'delegate': request.form.get('delegate') == 'True',
                  'tools': request.form.getlist('tools'),
                  'pydantic_class': request.form.get('pydantic_class')
              }

              if action == 'add':
                  tasks.append({'Task': task_data})
                  flash('Task added successfully', 'success')
              elif action == 'edit':
                  index = int(request.form.get('index', -1))
                  if 0 <= index < len(tasks):
                      tasks[index]['Task'] = task_data
                      flash('Task updated successfully', 'success')

          elif action == 'delete':
              index = int(request.form.get('index', -1))
              if 0 <= index < len(tasks):
                  del tasks[index]
                  flash('Task deleted successfully', 'success')

          # Save changes to YAML file
          with open('config/tasks.yaml', 'w') as f:
              yaml.dump(tasks, f, default_flow_style=False)

          return redirect(url_for('manage_tasks'))

      except Exception as e:
          app.logger.error(f"Error processing task form: {str(e)}")
          flash('Error processing form submission', 'error')
          return redirect(url_for('manage_tasks'))

  try:
      # Get available tools from app_state
      available_tools = list(app_state.tools.keys()) if app_state.tools else []
      logger.info(f"Available tools: {available_tools}")

      # Load tasks
      try:
          with open('config/tasks.yaml', 'r') as f:
              tasks = yaml.safe_load(f) or []
      except Exception as e:
          logger.error(f"Error loading tasks.yaml: {str(e)}")
          flash('Error loading tasks data', 'error')

      # Load agents
      try:
          with open('config/agents.yaml', 'r') as f:
              agents = yaml.safe_load(f) or []
      except Exception as e:
          logger.error(f"Error loading agents.yaml: {str(e)}")
          flash('Error loading agents data', 'error')

      # Process tasks to ensure tools property exists
      for task in tasks:
          if 'Task' in task:
              if 'tools' not in task['Task'] or task['Task']['tools'] is None:
                  task['Task']['tools'] = []

      # Enhanced logging for debugging
      logger.info("=== Debug Information ===")
      logger.info(f"Tasks count: {len(tasks)}")
      logger.info(f"Agents count: {len(agents)}")
      logger.info(f"Available tools: {available_tools}")
      logger.info(f"Pydantic classes: {enhanced_pydantic_classes}")

      # Enhance pydantic_class_dict with descriptions
      """
      enhanced_pydantic_classes = {
          'Engineered Prompt': {
              'path': 'self_eval_crew.EngineeredPrompt',
              'description': 'Structures output as a prompt with rationale for changes. Use for prompt engineering tasks.'
          },
          'Analysis Review State': {
              'path': 'self_eval_crew.AnalysisReviewState',
              'description': 'Tracks analysis state with counter, prompt, rationale, and feedback. Use for review tasks.'
          },
          'Research Results': {
              'path': 'self_eval_crew.ResearchResults',
              'description': 'Organizes research findings in a structured dictionary format. Use for research tasks.'
          },
          'None': {
              'path': '',
              'description': 'No specific output format required. Task will return raw output.'
          }
      }
      """

      return render_template('tasks.html',
                          tasks=tasks,
                          tasks_json=json.dumps(tasks),
                          agents=agents,
                          tools=available_tools,
                          pydantic_classes=enhanced_pydantic_classes,
                          csrf_token=generate_csrf())

  except Exception as e:
      logger.error(f"Error in manage_tasks: {str(e)}")
      flash('An unexpected error occurred', 'error')
      return render_template('tasks.html', 
                          tasks=[],
                          tasks_json="[]",
                          agents=[],
                          tools=[],
                          pydantic_classes={},
                          csrf_token=generate_csrf())

def manage_agents_helper(app_state):
    """Handle agent management operations"""
    logger.info("Accessing manage_agents route")
    try:
        # Handle POST request for agent updates
        if request.method == 'POST':
            try:
                logger.info("Processing POST request for agent management")
                form_data = request.form

                # Verify CSRF token
                if not form_data.get('csrf_token'):
                    logger.error("CSRF token missing")
                    flash('Invalid form submission', 'error')
                    return redirect(url_for('manage_agents'))

                # Load current agents
                with open('config/agents.yaml', 'r') as f:
                    agents = yaml.safe_load(f) or []

                action = form_data.get('action')
                logger.info(f"Agent form action: {action}")

                if action in ['add', 'edit']:
                    agent_data = {
                        'name': form_data.get('name'),
                        'role': form_data.get('role'),
                        'goal': form_data.get('goal'),
                        'backstory': form_data.get('backstory'),
                        'delegate': form_data.get('delegate') == 'True',
                        'tools': request.form.getlist('tools') if request.form.getlist('tools') else []
                    }

                    if action == 'add':
                        agents.append({'Agent': agent_data})
                        flash('Agent added successfully', 'success')
                    elif action == 'edit':
                        index = int(form_data.get('index', -1))
                        if 0 <= index < len(agents):
                            agents[index]['Agent'] = agent_data
                            flash('Agent updated successfully', 'success')

                elif action == 'delete':
                    index = int(form_data.get('index', -1))
                    if 0 <= index < len(agents):
                        del agents[index]
                        flash('Agent deleted successfully', 'success')

                # Save changes to YAML file
                with open('config/agents.yaml', 'w') as f:
                    yaml.dump(agents, f, default_flow_style=False)

                return redirect(url_for('manage_agents'))

            except Exception as e:
                logger.error(f"Error processing agent form: {str(e)}")
                flash('Error processing form submission', 'error')
                return redirect(url_for('manage_agents'))

        # Load current data for GET request or after POST
        with open('config/agents.yaml', 'r') as f:
            agents = yaml.safe_load(f) or []
        # Get available tools from app_state
        available_tools = list(app_state.tools.keys()) if app_state.tools else []
        logger.debug(f"Loaded {len(agents)} agents and {len(available_tools)} tools")

        return render_template('agents.html',
                           agents=agents,
                           tools=available_tools,
                           agents_json=json.dumps(agents),
                           csrf_token=generate_csrf())

    except Exception as e:
        logger.error(f"Error in manage_agents: {str(e)}", exc_info=True)
        flash('An error occurred while processing your request', 'error')
        return render_template('agents.html',
                           agents=[],
                           tools=[],
                           agents_json="[]",
                           csrf_token=generate_csrf())

def manage_crews_helper(app_state):
    """Handle crew management operations"""
    logger.info("Accessing manage_crews route")
    try:
        if request.method == 'POST':
            try:
                # Load current crews
                with open('config/crews.yaml', 'r') as f:
                    crews = yaml.safe_load(f) or []

                action = request.form.get('action')
                logger.info(f"Crew form action: {action}")

                if action in ['add', 'edit']:
                    crew_data = {
                        'name': request.form.get('name'),
                        'agents': request.form.getlist('agents'),
                        'tasks': request.form.getlist('tasks')
                    }

                    if action == 'add':
                        crews.append({'Crew': crew_data})
                        flash('Crew added successfully', 'success')
                    elif action == 'edit':
                        index = int(request.form.get('index', -1))
                        if 0 <= index < len(crews):
                            crews[index]['Crew'] = crew_data
                            flash('Crew updated successfully', 'success')

                elif action == 'delete':
                    index = int(request.form.get('index', -1))
                    if 0 <= index < len(crews):
                        del crews[index]
                        flash('Crew deleted successfully', 'success')

                # Save changes to YAML file
                with open('config/crews.yaml', 'w') as f:
                    yaml.dump(crews, f, default_flow_style=False)

                return redirect(url_for('manage_crews'))

            except Exception as e:
                logger.error(f"Error processing crew form: {str(e)}")
                flash('Error processing form submission', 'error')
                return redirect(url_for('manage_crews'))
    except Exception as e:
        logger.error(f"Error processing crew form: {str(e)}")
        flash('Error processing form submission', 'error')
        return redirect(url_for('manage_crews'))

    # Load data for GET request or after POST
    with open('config/crews.yaml', 'r') as f:
            crews = yaml.safe_load(f) or []
    with open('config/agents.yaml', 'r') as f:
            agents = yaml.safe_load(f) or []
    with open('config/tasks.yaml', 'r') as f:
            tasks = yaml.safe_load(f) or []
    logger.debug(f"Loaded {len(crews)} crews, {len(agents)} agents, and {len(tasks)} tasks")

    return render_template('crews.html',
                           crews=crews,
                           agents=agents,
                           tasks=tasks,
                           agents_json=json.dumps(agents),
                           tasks_json=json.dumps(tasks),
                           csrf_token=generate_csrf())