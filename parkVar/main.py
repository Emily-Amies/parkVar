import shutil
from pathlib import Path
import os

if __name__ == '__main__':
    
    # Delete the data directory at the start of each session. If this is not 
    # done, data from the previous session will be used.
    data_dir = '../data'
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)

    # Create a logs directory if one doesn't exist. This is because it is not
    # included in the GitHub repo
    log_dir = '../logs'
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    # This is here (not at the top) because the logs directory needs to be 
    # made before the import
    from parkVar.modules.flask_app import app

    # Run the app
    app.run(host='127.0.0.1', port=5000, debug=True)