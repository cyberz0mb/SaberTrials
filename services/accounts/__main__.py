import sys
from .runtime import main

try:
    main()
except Exception:
    # A traceback could expose deployment configuration or future credentials.
    print('Account service could not start. Check required configuration and persistent storage.', file=sys.stderr)
    raise SystemExit(1)
