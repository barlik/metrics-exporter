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

cfg = None
plugins = None
plugins_dir = "plugins"
log = logging.getLogger()

exceptions = Counter(
    name="exceptions",
    documentation="Number of plugin exceptions",
    labelnames=["plugin"],
)

timeouts = Counter(
    name="exporter_timeouts",
    documentation="Number of plugin timeouts",
    labelnames=["plugin"],
)

scrape_plugin_duration_seconds = Gauge(
    name="scrape_plugin_duration_seconds",
    documentation="Duration of collector plugin scrape",
    labelnames=["plugin"],
)

loaded_plugins = Info("exporter_plugins", "Loaded plugins")


class MyCollector:
    def collect(self):
        start = default_timer()

        executor = Executor(max_workers=len(plugins))
        futures = {
            executor.submit(plugin.run): name for name, plugin in plugins.items()
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
                    log.error("plugin %r generated an exception", fn_name)
                else:
                    duration = max(default_timer() - start, 0)
                    scrape_plugin_duration_seconds.labels(fn_name).set(duration)
                    log.debug("%s finished in %.02fs", fn_name, duration)
        except concurrent.futures.TimeoutError:
            for future, fn_name in futures.items():
                if not future.done():
                    timeouts.labels(fn_name).inc()
                    log.error("plugin %r timeout exceeded", fn_name)

        log.info("Scrape complete")
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exporter")
    parser.add_argument("config", help="config file to use")

    args = parser.parse_args(sys.argv[1:])

    global cfg
    cfg = config.config = config.Config(args.config)
    logging.basicConfig(level=cfg.log_level, format=cfg.log_format)

    plugins_path = os.path.join(os.path.dirname(__file__), plugins_dir)
    global plugins
    plugins = {
        name: importlib.import_module(f"{plugins_dir}.{name}")
        for finder, name, ispkg in pkgutil.iter_modules([plugins_path])
        if name in cfg.enabled_plugins
    }
    if not plugins:
        log.critical("No plugins enabled")
        sys.exit(1)
    log.info("Loaded plugins: %s", ", ".join(list(plugins)))

    loaded_plugins.info({plugin: "1" for plugin in plugins})

    REGISTRY.register(MyCollector())

    start_http_server(8000)
    while True:
        time.sleep(1)
