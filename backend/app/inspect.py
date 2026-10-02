import json
import sys

from .extractor import inspect
from .security import install_network_guard

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        install_network_guard()
        print(json.dumps(inspect(sys.argv[1]), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc)[-1200:]}, ensure_ascii=False))
        sys.exit(1)
