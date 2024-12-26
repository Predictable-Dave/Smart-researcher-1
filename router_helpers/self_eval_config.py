from flask import render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from flask_wtf.csrf import generate_csrf
from flask_wtf.csrf import CSRFError
import logging
import pandas as pd


# Import required packages with error handling
try:
    import pandas as pd
except ImportError:
    pd = None  # Handle case where pandas is not available
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def research_config_helper():
  try:
      if request.method == 'POST':
          configs = {'configs': []}
          with open('config/smart_research.yaml', 'r') as f:
              configs = yaml.safe_load(f) or {'configs': []}

          action = request.form.get('action')
          if action in ['add_config', 'edit_config']:
              config_data = {
                  'name': request.form.get('config_name'),
                  'prompt_engineer_crew': request.form.get('prompt_engineer_crew'),
                  'research_crew': request.form.get('research_crew'),
                  'research_review_crew': request.form.get('research_review_crew')
              }

              if action == 'add_config':
                  configs['configs'].append(config_data)
              elif action == 'edit_config':
                  config_name = request.form.get('config_name')
                  for i, config in enumerate(configs['configs']):
                      if config['name'] == config_name:
                          configs['configs'][i] = config_data
                          break

              with open('config/smart_research.yaml', 'w') as f:
                  yaml.dump(configs, f)

          elif action == 'delete_config':
              config_name = request.form.get('config_name')
              configs['configs'] = [c for c in configs['configs'] if c['name'] != config_name]
              with open('config/smart_research.yaml', 'w') as f:
                  yaml.dump(configs, f)

          return redirect(url_for('research_config'))

      with open('config/smart_research.yaml', 'r') as f:
          configs = yaml.safe_load(f) or {'configs': []}
      with open('config/crews.yaml', 'r') as f:
          crews = yaml.safe_load(f) or []
      with open('config/tasks.yaml', 'r') as f:
          tasks = yaml.safe_load(f) or []

      return render_template('research_config.html',
                          configs=configs['configs'],
                          crews=crews,
                          tasks=tasks,
                          smart_research_configs=configs['configs'],
                          csrf_token=generate_csrf())

  except Exception as e:
      logger.error(f"Error in research_config: {str(e)}")
      return render_template('research_config.html',
                          configs=[],
                          crews=[],
                          tasks=[],
                          smart_research_configs=[],
                          csrf_token=generate_csrf())
