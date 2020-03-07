"""
Sample plugin

Exposed metrics:
- sample_metric
"""
import logging

from prometheus_client import Gauge

from config import config

log = logging.getLogger(__name__)

sample = Gauge(
    name="sample_metric",
    documentation="Sample doc",
    labelnames=["mylabel"]
)


def run():
    """
    Collector
    """
    sample.labels(mylabel="test").set(config.scrape_timeout_seconds)
