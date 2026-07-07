import logging
from logging.handlers import RotatingFileHandler

LOG_FILE = "forexai.log"
LOG_LEVEL = logging.INFO

logger = logging.getLogger("forexai")
logger.setLevel(LOG_LEVEL)
handler = RotatingFileHandler(LOG_FILE, maxBytes=5_242_880, backupCount=3, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
