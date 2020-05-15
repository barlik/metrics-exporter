import argparse
import concurrent.futures
import importlib
import logging
import os
import pkgutil
import sys
import time
from timeit import default_timer

from prometheus_client import Counter, Gauge, Info, start_http_server
from prometheus_client.core import REGISTRY

import config
from utils.threadpool import ThreadPoolExecutorDumpStacktrace as Executor

collectors_dir = "collectors"
log = logging.getLogger()

exceptions = Counter(
    name="scrape_collector_exceptions",
    documentation="Number of collector exceptions",
    labelnames=["collector"],
)

success = Gauge(
    name="scrape_collector_success",
    documentation="Whether the collector succeeded",
    labelnames=["collector"],
)

scrape_collector_duration_seconds = Gauge(
    name="scrape_collector_duration_seconds",
    documentation="Duration of collector collector scrape",
    labelnames=["collector"],
)

loaded_collectors = Info("exporter_collectors", "Loaded collectors")


class MyCollector:
    def collect(self):
        start = default_timer()

        executor = Executor(max_workers=len(collectors))
        futures = {
            executor.submit(collector.collect): name for name, collector in collectors.items()
        }
        try:
            for future in concurrent.futures.as_completed(
                futures, timeout=cfg.scrape_timeout_seconds
            ):
                fn_name = futures[future]
                try:
                    future.result()
                except Exception:
                    exceptions.labels(fn_name).inc()
                    log.error("collector %r generated an exception", fn_name)
                else:
                    success.labels(fn_name).set(1)

                    duration = max(default_timer() - start, 0)
                    scrape_collector_duration_seconds.labels(fn_name).set(duration)

                    log.debug("%s finished in %.02fs", fn_name, duration)
        except concurrent.futures.TimeoutError:
            for future, fn_name in futures.items():
                if not future.done():
                    success.labels(fn_name).set(0)
                    log.error("collector %r timeout exceeded", fn_name)

        log.info("Scrape complete in %.02fs", default_timer() - start)
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exporter")
    parser.add_argument("config", help="config file to use")

    args = parser.parse_args(sys.argv[1:])

    global cfg
    cfg = config.config = config.Config(args.config)
    logging.basicConfig(level=cfg.log_level, format=cfg.log_format)

    collectors_path = os.path.join(os.path.dirname(__file__), collectors_dir)
    global collectors
    collectors = {
        name: importlib.import_module(f"{collectors_dir}.{name}")
        for finder, name, ispkg in pkgutil.iter_modules([collectors_path])
        if name in cfg.enabled_collectors
    }
    if not collectors:
        log.critical("No collectors enabled")
        sys.exit(1)
    log.info("Loaded collectors: %s", ", ".join(list(collectors)))

    loaded_collectors.info({collector: "1" for collector in collectors})

    REGISTRY.register(MyCollector())

    start_http_server(8000)
    while True:
        time.sleep(1)
