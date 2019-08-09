
import sys


class Stdout:

    def __init__(self, meta, config):
        return

    @property
    def target(self):
        return sys.stdout

    @property
    def closed(self):
        return False

    def close(self):
        return

