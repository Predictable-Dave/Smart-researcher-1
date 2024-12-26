from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_wtf.csrf import generate_csrf
from flask_wtf.csrf import CSRFError
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from db_utils import get_cached_results, get_cache_files, query_vector_cache

# Import required packages with error handling
try:
    import pandas as pd
except ImportError:
    pd = None  # Handle case where pandas is not available


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _query_helper(query):
    """Helper function to handle vector database queries"""
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    try:
        results = query_vector_cache(query)
        if not results or not results.get('ids'):
            return jsonify({'error': 'No results found'}), 404
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error querying vector database: {str(e)}")
        return jsonify({'error': str(e)}), 400

def _clear_temp_helper():
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

def _clear_logs_helper():
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

def _clear_dbcache_helper():
    """Helper function to clear cache database files"""
    try:
        logger.info("Clearing cache database files")
        cache_dir = Path('cache')
        if not cache_dir.exists():
            logger.info("Cache directory does not exist, creating it")
            cache_dir.mkdir(exist_ok=True)
            return redirect(url_for('maintenance'))

        files_deleted = False
        for file in cache_dir.glob('*'):
            if file.is_file():
                try:
                    # Check if file is not in use
                    if not file.name.startswith('.'):  # Skip hidden files
                        file.unlink(missing_ok=True)
                        files_deleted = True
                except Exception as e:
                    logger.error(f"Error deleting cache file {file}: {str(e)}")
                    continue

        if files_deleted:
            flash('Cache files cleared successfully', 'success')
        else:
            flash('No cache files to clear', 'info')

    except Exception as e:
        logger.error(f"Error in clear cache operation: {str(e)}")
        flash('Error clearing cache files', 'error')
    return redirect(url_for('maintenance'))

def maintenance_helper():
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

            if action == 'query_vector_db':
                query = request.form.get('vector_query', '')
                return _query_helper(query)


            elif action == 'clear_temp':
                return _clear_temp_helper()


            elif action == 'clear_logs':
                return _clear_logs_helper()


            elif action == 'clear_cache_dbs':
                return _clear_dbcache_helper()

            else:
              flash('Invalid action', 'error')
              return redirect(url_for('maintenance'))

        # Get list of files for display
        try:
            temp_dir = Path('temp')
            log_dir = Path('logs')

            # Create directories if they don't exist
            temp_dir.mkdir(exist_ok=True)
            log_dir.mkdir(exist_ok=True)

            temp_files = []
            log_files = []

            # List temp files safely
            if temp_dir.exists():
                for file in temp_dir.glob('*'):
                    try:
                        if file.is_file() and not file.name.startswith('.'):
                            stat = file.stat()
                            temp_files.append({
                                'name': file.name,
                                'date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                            })
                    except (OSError, IOError) as e:
                        logger.error(f"Error accessing temp file {file}: {str(e)}")
                        continue
                    except Exception as e:
                        logger.error(f"Unexpected error processing temp file {file}: {str(e)}")
                        continue

            # List log files safely
            if log_dir.exists():
                for file in log_dir.glob('*.log'):
                    try:
                        if file.is_file() and not file.name.startswith('.'):
                            stat = file.stat()
                            log_files.append({
                                'name': file.name,
                                'date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                            })
                    except (OSError, IOError) as e:
                        logger.error(f"Error accessing log file {file}: {str(e)}")
                        continue
                    except Exception as e:
                        logger.error(f"Unexpected error processing log file {file}: {str(e)}")
                        continue

        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            temp_files = []
            log_files = []

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