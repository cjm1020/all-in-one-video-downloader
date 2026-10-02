import sys

from . import db
from .status import worker_healthy

if __name__ == "__main__":
    db.initialize()
    sys.exit(0 if worker_healthy() else 1)
