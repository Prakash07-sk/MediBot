import logging

# Create a custom logger
logger = logging.getLogger("app_logger")
logger.setLevel(logging.INFO)

# Create handler
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

# Create formatter with date and time
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Add formatter to handler
handler.setFormatter(formatter)

# Add handler to logger if not already added
if not logger.hasHandlers():
    logger.addHandler(handler)
