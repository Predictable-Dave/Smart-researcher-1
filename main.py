from flask import Flask
import logging
import os
from routes import register_routes
from app_state import AppState
from flask_wtf.csrf import CSRFProtect, CSRFError

# Configure enhanced logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/flask_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    
    try:
        # Create Flask app
        logger.info("Creating Flask application...")
        app = Flask(__name__)
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-please-change')
        app.config['DEBUG'] = True
        
        # Initialize CSRF protection
        logger.info("Initializing CSRF protection...")
        try:
            csrf = CSRFProtect()
            csrf.init_app(app)
            logger.info("CSRF protection initialized successfully")
            
            # Add CSRF error handler
            @app.errorhandler(CSRFError)
            def handle_csrf_error(e):
                logger.error(f"CSRF error occurred: {str(e)}")
                return f"CSRF token validation failed: {e.description}", 400
            logger.info("CSRF error handler registered")
        except Exception as e:
            logger.error(f"Failed to initialize CSRF protection: {str(e)}", exc_info=True)
            raise

        # Initialize AppState
        logger.info("Initializing AppState...")
        try:
            app_state = AppState()
            logger.info("AppState initialization successful")
        except Exception as e:
            logger.error(f"Failed to initialize AppState: {str(e)}", exc_info=True)
            raise
        
        # Register routes
        logger.info("Registering routes...")
        try:
            register_routes(app, app_state)
            logger.info("Routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register routes: {str(e)}", exc_info=True)
            raise
        
        return app, app_state
    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':

    try:
        # Initialize required modules
        import sys
        import traceback
        
        logger.info("Starting Flask server initialization...")
        try:
            app, app_state = create_app()
            logger.info("Flask server initialization complete, starting server...")
            logger.info("Starting Flask server on port 5000...")
            logger.debug("Flask app configuration: %s", app.config)
            app.run(host='0.0.0.0', port=5000, debug=True)
        except ImportError as ie:
            logger.critical(f"Missing required module: {str(ie)}")
            traceback.print_exc()
            sys.exit(1)
        except Exception as e:
            logger.critical(f"Failed to start Flask server: {str(e)}")
            logger.critical(f"Stack trace: {traceback.format_exc()}")
            sys.exit(1)
    except Exception as e:
        logger.critical(f"Critical error in main: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
