from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from flask_wtf.csrf import generate_csrf
from flask_wtf.csrf import CSRFError
import logging
import json
import pandas as pd
from datetime import datetime
import yaml
from pathlib import Path

# Import required packages with error handling
try:
    import pandas as pd
except ImportError:
    pd = None  # Handle case where pandas is not available
from datetime import datetime
import json
import yaml
import logging
from pathlib import Path
#from task_outputs import pydantic_class_dict
from excel_output import create_pivot_table_df,load_json_data
from result_formatter import result_formatter
from router_helpers.execute import execute_crew_helper,execute_self_eval_crew_helper
from router_helpers.crew_config import manage_tasks_helper,manage_agents_helper,manage_crews_helper
from router_helpers.inputs_config import manage_files_helper, manage_inputs_helper
from router_helpers.self_eval_config import research_config_helper
from router_helpers.downloads import download_json_helper, download_excel_helper
from router_helpers.maintenance import maintenance_helper
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_routes(app, app_state):
    """Register all application routes"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.info("Starting route registration...")
    
    # Register CSRF error handler
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        logger.error(f"CSRF error occurred: {str(e)}")
        # Always return JSON for API endpoints
        if request.path in ['/execute_crew', '/execute_self_eval_crew'] or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'CSRF token validation failed. Please refresh and try again.'}), 400
        return render_template('error.html', error="CSRF token validation failed. Please try again."), 400

    def _home():
        try:
            with open('config/crews.yaml', 'r') as f:
                crews = yaml.safe_load(f) or []
            with open('config/smart_research.yaml', 'r') as f:
                smart_research = yaml.safe_load(f) or {'configs': []}
        except Exception as e:
            app.logger.error(f"Error loading data: {str(e)}")
            crews = []
            smart_research = {'configs': []}
        return render_template('home.html', crews=crews, smart_research_configs=smart_research['configs'])
            

            
    @app.route('/')
    def home():
        return _home()
 

    @app.route('/execute_self_eval_crew', methods=['POST'])
    def execute_self_eval_crew():
        return execute_self_eval_crew_helper(app_state=app_state)

    @app.route('/execute_crew', methods=['POST'])
    def execute_crew():
        return execute_crew_helper(app_state)

    @app.route('/download_json/<filename>')
    def download_json(filename):
        return download_json_helper(filename=filename)
            
    @app.route('/download_excel/<filename>')
    def download_excel(filename):
        return download_excel_helper(filename=filename)
        #return _download_excel(filename)


    @app.route('/research_config', methods=['GET', 'POST'])
    def research_config():
        return research_config_helper()


    @app.route('/manage_tasks', methods=['GET', 'POST'])
    @app.route('/tasks', methods=['GET', 'POST'])  # Add an alias route for convenience
    def manage_tasks():
        return manage_tasks_helper(app_state=app_state)


    @app.route('/manage_agents', methods=['GET', 'POST'])
    @app.route('/agents', methods=['GET', 'POST'])  # Add an alias route for convenience
    def manage_agents():
        return manage_agents_helper(app_state=app_state)


    @app.route('/manage_crews', methods=['GET', 'POST'])
    @app.route('/crews', methods=['GET', 'POST'])  # Add an alias route for convenience
    def manage_crews():
        return manage_crews_helper(app_state=app_state)


    @app.route('/manage_inputs', methods=['GET', 'POST'])
    def manage_inputs():
        return manage_inputs_helper()

    @app.route('/manage_files', methods=['GET', 'POST'])
    def manage_files():
        app.logger.error("calling manage_files_helper")
        return manage_files_helper()

    @app.route('/maintenance', methods=['GET', 'POST'])
    def maintenance():
        return maintenance_helper()
        """Handle maintenance operations like clearing logs and temp files"""
        logger.info("Accessing maintenance page")
        
        try:
            if request.method == 'POST':
                # Verify CSRF token
                csrf_token = request.form.get('csrf_token')
                if not csrf_token:
                    flash('CSRF token missing', 'error')
                    return redirect(url_for('maintenance'))

                action = request.form.get('action')
                
                if action == 'clear_temp':
                    logger.info("Clearing temp files")
                    temp_dir = Path('temp')
                    temp_dir.mkdir(exist_ok=True)
                    for file in temp_dir.glob('*'):
                        if file.is_file():
                            try:
                                file.unlink()
                            except Exception as e:
                                logger.error(f"Error deleting temp file {file}: {str(e)}")
                    flash('Temporary files cleared successfully', 'success')
                    return redirect(url_for('maintenance'))
                
                elif action == 'clear_logs':
                    logger.info("Clearing log files")
                    log_dir = Path('logs')
                    log_dir.mkdir(exist_ok=True)
                    for file in log_dir.glob('*.log'):
                        if file.is_file():
                            try:
                                # Don't delete the current log files
                                if file.name not in ['flask_app.log', 'app_state.log']:
                                    file.unlink()
                            except Exception as e:
                                logger.error(f"Error deleting log file {file}: {str(e)}")
                    flash('Log files cleared successfully', 'success')
                    return redirect(url_for('maintenance'))

                elif action == 'clear_cache_dbs':
                    logger.info("Clearing cache database files")
                    cache_dir = Path('cache')
                    cache_dir.mkdir(exist_ok=True)
                    for file in cache_dir.glob('*.db'):
                        if file.is_file():
                            try:
                                file.unlink()
                            except Exception as e:
                                logger.error(f"Error deleting cache database {file}: {str(e)}")
                    flash('Cache databases cleared successfully', 'success')
                    return redirect(url_for('maintenance'))
                
                else:
                    flash('Invalid action', 'error')
                    return redirect(url_for('maintenance'))

            # Get list of files for display
            temp_dir = Path('temp')
            log_dir = Path('logs')
            temp_dir.mkdir(exist_ok=True)
            log_dir.mkdir(exist_ok=True)
            
            temp_files = []
            log_files = []
            
            # List temp files
            for file in temp_dir.glob('*'):
                if file.is_file():
                    temp_files.append({
                        'name': file.name,
                        'date': datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            # List log files
            for file in log_dir.glob('*.log'):
                if file.is_file():
                    log_files.append({
                        'name': file.name,
                        'date': datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            # Get cached results and database files
            cached_results = get_cached_results()
            cache_files = get_cache_files()

            return render_template('maintenance.html',
                                temp_files=sorted(temp_files, key=lambda x: x['date'], reverse=True),
                                log_files=sorted(log_files, key=lambda x: x['date'], reverse=True),
                                cached_results=cached_results,
                                cache_files=cache_files)
                                
        except Exception as e:
            logger.error(f"Error in maintenance page: {str(e)}")
            flash('An error occurred while accessing maintenance page', 'error')
            return render_template('maintenance.html',
                                temp_files=[],
                                log_files=[],
                                cached_results=[],
                                cache_files=[])

    return app