#!/usr/bin/python3

from contextlib import contextmanager
import json
import signal
import ssl
import sys
import logging
import threading
import time
from prometheus_client import Gauge, start_http_server
import logging
import jq

import urllib
import yaml

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GracefulShutdown:
    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        signals = {signal.SIGTERM: 'SIGTERM', signal.SIGINT: 'SIGINT'}
        logger.warning(f"Received {signals.get(signum)} signal, initiating graceful shutdown...")
        self.shutdown_requested = True

    @contextmanager
    def interruptible_sleep(self, duration):
        """Sleep that can be interrupted by shutdown signal"""
        end_time = time.time() + duration
        while time.time() < end_time and not self.shutdown_requested:
            time.sleep(min(0.5, end_time - time.time()))
        yield

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
    shutdown = GracefulShutdown()

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
    scrape_interval = config.get('source', {}).get('scrape_interval', 60)
    logger.warning("Fetching data from %s every %d seconds", uri, scrape_interval)

    # Create an SSL context that ignores certificate verification
    if config.get('source', {}).get('insecure', False):
        context = ssl._create_unverified_context()
    else:
        context = ssl.create_default_context()

    while not shutdown.shutdown_requested:
        try:
            json = load_json_from_uri(uri, context)
            logger.info("Loaded JSON from %s", uri)
            logger.debug("JSON: %s", json)
            for gauge in gauges:
                gauge.set(json)

        except Exception as e:
            logger.error(f"Error in main loop: {e}")

        finally:
            with shutdown.interruptible_sleep(scrape_interval):
                pass

    logger.warning("Shutting down gracefully...")
    sys.exit(0)

if __name__ == '__main__':
    # Read config file from command line argument, default to "config.yml"
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yml"
    config = load_config(config_file)

    main(config)