from flask import request, jsonify
import os
import logging
import json
import pandas as pd
from datetime import datetime
from datetime import datetime
from result_formatter import result_formatter

# Import required packages with error handling
try:
    import pandas as pd
except ImportError:
    pd = None  # Handle case where pandas is not available

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def execute_crew_helper(app_state):
  """Execute a crew and return JSON response"""
  if request.method != 'POST':
      return jsonify({'error': 'Method not allowed'}), 405

  try:
      # Always return JSON for API endpoints
      if not request.is_json and request.headers.get('Accept') != 'application/json':
          return jsonify({'error': 'Invalid content type. Expected JSON request'}), 415

      # Get CSRF token from either header or form
      csrf_token = request.headers.get('X-CSRF-TOKEN') or request.form.get('csrf_token')
      if not csrf_token:
          return jsonify({'error': 'CSRF token missing'}), 400

      crew_name = request.form.get('crew_name')
      if not crew_name:
          return jsonify({'error': 'No crew name provided'}), 400

      logger.info(f"Attempting to execute crew: {crew_name}")

      from crew_manager import CrewManager
      crew_manager = CrewManager(app_state.agent_manager, app_state.task_manager)
      logger.debug(f"Available crews: {[c.get('Crew', {}).get('name') for c in crew_manager.crews if c]}")

      result = crew_manager.execute_crew(crew_name)
      logger.info(f"Execution result for crew {crew_name}: {result}")

      if 'error' in result:
          logger.error(f"Error executing crew {crew_name}: {result['error']}")
          return jsonify({'error': result['error']}), 500

      # Create temp directory if it doesn't exist
      os.makedirs('temp', exist_ok=True)

      # Generate unique filename using timestamp
      #timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
      filename = f"crew_{int(datetime.now().timestamp() * 1000)}"
      file_path = os.path.join('temp', f"{filename}.json")

      # Save results to JSON file
      try:
          with open(file_path, 'w') as f:
              json.dump(result, f, indent=2)
          logger.info(f"Saved crew results to {file_path}")

          # Try to format the result using a formatting agent
          formatted_result = result['result']  # Default to unformatted result
          try:
              formatted_result=result_formatter(formatted_result)
              logger.info("Successfully formatted result using formatting agent")
          except Exception as e:
              logger.error(f"Error formatting result: {str(e)}")
              logger.warning("Using raw result due to formatting error")

          return jsonify({
              'result': result['result'],
              'formatted_result': formatted_result,
              'filename': filename
          }), 200
      except Exception as e:
          logger.error(f"Error saving crew results to file: {str(e)}")
          return jsonify(result), 200

  except Exception as e:
      error_msg = f"Error executing crew: {str(e)}"
      logger.error(error_msg)
      return jsonify({'error': error_msg}), 500

def execute_self_eval_crew_helper(app_state):
    """Execute a self-evaluating crew and return JSON response"""
    if request.method != 'POST':
        return jsonify({'error': 'Method not allowed'}), 405

    try:
        # Always return JSON for API endpoints
        if not request.is_json and request.headers.get('Accept') != 'application/json':
            return jsonify({'error': 'Invalid content type. Expected JSON request'}), 415

        # Get CSRF token from either header or form
        csrf_token = request.headers.get('X-CSRF-TOKEN') or request.form.get('csrf_token')
        if not csrf_token:
            return jsonify({'error': 'CSRF token missing'}), 400

        prompt = request.form.get('prompt')
        crew_name = request.form.get('crew_name')
        if not prompt or not crew_name:
            return jsonify({'error': 'Missing prompt or crew name'}), 400

        logger.info(f"Attempting to execute self-evaluating crew with config: {crew_name}")

        # Initialize self-evaluating crew with the selected configuration
        from self_eval_crew import self_eval_crew
        researcher = self_eval_crew(crew_name)

        # Execute research
        result = researcher.run_research(prompt)
        logger.info(f"Execution result for self-evaluating crew: {result}")

        # Create temp directory if it doesn't exist
        os.makedirs('temp', exist_ok=True)

        # Generate unique filename using timestamp
        filename = f"self_eval_{int(datetime.now().timestamp() * 1000)}"
        file_path = os.path.join('temp', f"{filename}.json")

        # Save results to JSON file
        try:
            with open(file_path, 'w') as f:
                if isinstance(result, str):
                    json.dump({'result': result}, f, indent=2)
                else:
                    json.dump(result, f, indent=2)
            logger.info(f"Saved research results to {file_path}")

            # Try to format the result using a formatting agent
            formatted_result = result  # Default to unformatted result
            try:
                formatted_result = result_formatter(formatted_result)
                logger.info("Successfully formatted result using formatting agent")
            except Exception as e:
                logger.error(f"Error formatting result: {str(e)}")
                logger.warning("Using raw result due to formatting error")

            return jsonify({
                'result': result,
                'formatted_result': formatted_result,
                'filename': filename
            }), 200

        except Exception as e:
            logger.error(f"Error saving results to file: {str(e)}")
            return jsonify({'error': 'Error saving results'}), 500

    except Exception as e:
        error_msg = f"Error executing self-evaluating crew: {str(e)}"
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 500