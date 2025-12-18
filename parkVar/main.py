import os
from pathlib import Path

from parkVar.utils.logger_config import logger

if __name__ == '__main__':

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
    app.run(host='0.0.0.0', port=5000)


    # lsof -i :5000
    # kill -9 <id>
