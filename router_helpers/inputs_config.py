import os
import json
import logging
from pathlib import Path
from datetime import datetime
from flask import render_template, request, flash, redirect, url_for
from flask_wtf.csrf import generate_csrf
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def manage_inputs_helper():
    try:
        with open('config/inputs.json', 'r') as f:
            inputs = json.load(f)
    except Exception as e:
        logger.error(f"Error loading inputs: {str(e)}")
        inputs = {}

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add' or action == 'edit':
            name = request.form.get('name')
            value = request.form.get('value')
            if name and value:
                inputs[name] = value
        elif action == 'delete':
            name = request.form.get('name')
            if name in inputs:
                del inputs[name]

        try:
            with open('config/inputs.json', 'w') as f:
                json.dump(inputs, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving inputs: {str(e)}")
            flash('Error saving changes', 'error')

    return render_template('inputs.html', inputs=inputs, csrf_token=generate_csrf())

def manage_files_helper():
    """Handle file upload management"""
    logger.info("Accessing manage_files route")

    # Create required directories if they don't exist
    try:
        src_docs = Path('src_docs')
        processed_docs = src_docs / 'processed_docs'
        src_docs.mkdir(exist_ok=True)
        processed_docs.mkdir(exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating directories: {str(e)}")
        flash('Error initializing upload directories', 'error')
        return render_template('file_upload.html', 
                             pending_files=[], 
                             processed_files=[], 
                             csrf_token=generate_csrf())

    if request.method == 'POST':
        # Handle file upload
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('manage_files'))

        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('manage_files'))

        if not request.form.get('csrf_token'):
            flash('Invalid form submission', 'error')
            return redirect(url_for('manage_files'))

        # Validate file type
        allowed_extensions = {'.xlsx', '.xls', '.pdf'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            flash('Invalid file type. Only Excel and PDF files are allowed.', 'error')
            return redirect(url_for('manage_files'))

        try:
            filename = secure_filename(file.filename)
            file_path = os.path.join(src_docs, filename)
            file.save(file_path)
            flash('File uploaded successfully', 'success')
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            flash('Error saving uploaded file', 'error')

        return redirect(url_for('manage_files'))

    # List files in directories
    pending_files = []
    processed_files = []

    try:
        # Get pending files
        for file in os.listdir(src_docs):
            if file != 'processed_docs':
                file_path = os.path.join(src_docs, file)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    pending_files.append({
                        'name': file,
                        'type': os.path.splitext(file)[1][1:].upper(),
                        'upload_date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })

        # Get processed files
        for file in os.listdir(processed_docs):
            file_path = os.path.join(processed_docs, file)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                processed_files.append({
                    'name': file,
                    'type': os.path.splitext(file)[1][1:].upper(),
                    'processed_date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        flash('Error listing files', 'error')

    return render_template('file_upload.html',
                         pending_files=sorted(pending_files, key=lambda x: x['upload_date'], reverse=True),
                         processed_files=sorted(processed_files, key=lambda x: x['processed_date'], reverse=True),
                         csrf_token=generate_csrf())