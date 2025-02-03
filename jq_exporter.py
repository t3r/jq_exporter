#!/usr/bin/python3

import json
import ssl
import sys
import logging
import time
from prometheus_client import Gauge, start_http_server
import logging
import jq

import urllib
import yaml

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JsonGauge(Gauge):
    def __init__(self,
                name: str,
                documentation: str,
                query: str,
                namespace: str = None,
                unit: str = None,
                subsystem: str = None,
                factor=1 ):

        super().__init__(name=name,
                         documentation=documentation,
                         unit=unit,
                         namespace=namespace,
                         subsystem=subsystem)

        self._factor = factor
        self._query = jq.compile(query)

    def set(self, jsonValue, ):
        q = self._query.input(jsonValue).first()
        if q is None:
            q = 0
        logger.debug("Setting %s to %s", self._name, str(q))
        value = float(q)
        super().set(value * self._factor)

def load_config(config_file: str) -> any:
    try:
        with open(config_file, "r") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading config file {config_file}: {e}")
        sys.exit(1)



def load_json_from_uri(uri: str, context: ssl.SSLContext) -> any:
    if uri.startswith("file://"):
        file_path = uri[7:]  # Remove "file://" prefix
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    elif uri.startswith(("http://", "https://")):
        logger.debug("SSL Context verification mode: %s", context.verify_mode)
        with urllib.request.urlopen(uri, context=context) as response:
            return json.load(response)
    else:
        raise ValueError(f"Unsupported URI scheme: {uri}")

def main(config: any) -> None:
    logger.setLevel(config.get('log_level', 'WARNING'))
    # Create an SSL context that ignores certificate verification

    gauges = []
    namespace = config.get('namespace', 'jq')
    for entry in config.get('metrics', []):
        logger.info(f"Creating gauge for {entry}")
        gauge = JsonGauge(name=entry['name'],
                      namespace=namespace,
                      documentation=entry['description'],
                      unit=entry['unit'],
                      query=entry['query'])
        gauges.append(gauge)

    server_port: int = int(config.get('server', {}).get('port', 9000))
    server_address: str = config.get('server', {}).get('address', '127.0.0.1')
    start_http_server(port=server_port, addr=server_address)
    logger.warning("Server started on %s:%d", server_address, server_port)

    uri = config.get('source', {}).get('url', 'http://localhost/')
    logger.warning("Fetching data from %s", uri)

    if config.get('source', {}).get('insecure', False):
        context = ssl._create_unverified_context()
    else:
        context = ssl.create_default_context()

    scrape_interval = config.get('source', {}).get('scrape_interval', 60)
    while True:
        json = load_json_from_uri(uri, context)
        logger.debug("JSON: %s", json)
        for gauge in gauges:
            gauge.set(json)
        time.sleep(scrape_interval)


if __name__ == '__main__':
    # Read config file from command line argument, default to "config.yml"
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yml"
    config = load_config(config_file)

    main(config)
