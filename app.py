# This file is deprecated - all Flask initialization is now in main.py
from main import create_app

if __name__ == '__main__':
    print("Warning: Please use main.py directly. This file is maintained only for compatibility.")
    try:
        app, _ = create_app()
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"Error starting Flask server: {str(e)}")
        raise
