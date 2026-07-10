#!/usr/bin/env python3

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from dealwise.ui.app import DealWiseApplication


def main() -> int:
    try:
        app = DealWiseApplication()
        return app.run(None)
    except Exception:
        error_text = traceback.format_exc()
        log_path = Path("/tmp/dealwise_fatal.log")
        log_path.write_text(error_text, encoding="utf-8")
        print(error_text, file=sys.stderr)
        print(f"Fatal startup error saved to: {log_path}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
