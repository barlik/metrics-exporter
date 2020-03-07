import yaml


class Config:
    def __init__(self, filename):
        with open(filename, "r") as f:
            cfg = yaml.safe_load(f)

        self.scrape_timeout_seconds = cfg["scrape_timeout_seconds"]
        self.enabled_plugins = cfg["enabled_plugins"]
        self.log_level = cfg["log_level"]
        self.log_format = cfg["log_format"]

config: Config = None
