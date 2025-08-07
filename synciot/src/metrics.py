from tools.logger import get_logger

logger = get_logger("Metrics")


class Counter:
    def __init__(self, name):
        self.name = name
        self.value = 0

    def inc(self):
        self.value += 1

    def dec(self):
        self.value -= 1

    def get_value(self):
        return self.value

    def log_value(self):
        logger.info(f"{self.name}: {self.value}")

class Metrics:
    def __init__(self):
        self.metrics = {}

    def add_counter(self, name) -> Counter:
        counter = Counter(name)
        self.metrics[name] = counter
        return counter

    def get_metric(self, name):
        return self.metrics.get(name, None)

    def get_all_metrics(self):
        return self.metrics

    def log_values(self):
        for name, counter in self.metrics.items():
            counter.log_value()
