import os
from dotenv import load_dotenv
from influx.client import client
from influx.scripts import run_script
from loguru import logger


if __name__ == '__main__':
  try:
    path = 'latest_temperature.flux'
    r    = run_script([path])
    logger.debug(r.head())
  except Exception as e:
    logger.warning(e)

    