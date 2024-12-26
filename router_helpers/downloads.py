from flask import  redirect, url_for, flash, send_file
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
from excel_output import create_pivot_table_df,load_json_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_json_helper(filename):
  """Download research results as JSON"""
  try:
      # Create temp directory if it doesn't exist
      os.makedirs('temp', exist_ok=True)

      # Clean filename and ensure it only has the base name
      clean_filename = os.path.basename(filename)
      file_path = os.path.join('temp', f"{clean_filename}.json")

      logger.info(f"Attempting to download JSON file: {file_path}")

      if not os.path.exists(file_path):
          logger.error(f"File not found: {file_path}")
          flash('File not found', 'error')
          return redirect(url_for('home'))

      logger.info(f"File found, sending: {file_path}")
      return send_file(
          file_path,
          mimetype='application/json',
          as_attachment=True,
          download_name=f"research_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
      )
  except Exception as e:
      logger.error(f"Error downloading JSON: {str(e)}", exc_info=True)
      flash('Error downloading file', 'error')
      return redirect(url_for('home'))

def download_excel_helper(filename):
    """Download research results as Excel"""
    try:
        # Create temp directory if it doesn't exist
        os.makedirs('temp', exist_ok=True)
        json_file = os.path.join('temp', f"{filename}.json")
        excel_file = os.path.join('temp', f"{filename}.xlsx")

        if not os.path.exists(json_file):
            flash('Source file not found', 'error')
            return redirect(url_for('home'))

        # Convert JSON to Excel
        with open(json_file, 'r') as f:
            data = json.load(f)
        json_str=data['result']
        offset=json_str.find('{')
        negative_offset=json_str.rfind('}')
        json_str=json_str[offset:negative_offset+1]
        try:
            data=load_json_data(json_str)
            df = create_pivot_table_df(data)
        except json.JSONDecodeError as e:
            df = pd.DataFrame([data])

        df.to_excel(excel_file, index=False)

        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"research_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
    except Exception as e:
        app.logger.error(f"Error downloading Excel: {str(e)}")
        flash('Error downloading file', 'error')
        return redirect(url_for('home'))