# /influx/client.py

import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from loguru import logger

load_dotenv(encoding='utf-8', override=True)

url   = 'https://' + os.getenv('INFLUXDB_V2_URL')
token = os.getenv('INFLUXDB_V2_TOKEN')
org   = os.getenv('INFLUXDB_V2_ORG')
  
client = InfluxDBClient(url=url, token=token, org=org)
