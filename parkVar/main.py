import shutil
from pathlib import Path
import os
from parkVar.utils.logger_config import logger

if __name__ == '__main__':
    
    # Delete the data directory at the start of each session. If this is not 
    # done, data from the previous session will be used.
    # data_dir = '../data'
    # if os.path.isdir(data_dir):
    #     shutil.rmtree(data_dir)

    # Delete all files in the temporary data directory
    data_dir = Path(__file__).resolve().parent.parent / "data"

    for item in data_dir.glob("*"):
        try:
            item.unlink()
        except Exception as e:
            logger.error(f"Failed to delete {item}: {e}")

    logger.info("Data directory deleted")


    # Create a logs directory if one doesn't exist. This is because it is not
    # included in the GitHub repo
    log_dir = '../logs'
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    # This is here (not at the top) because the logs directory needs to be 
    # made before the import
    from parkVar.modules.flask_app import app

    # Run the app
    app.run(host='127.0.0.1', port=5000)


    # lsof -i :5000
    # kill -9 <id>