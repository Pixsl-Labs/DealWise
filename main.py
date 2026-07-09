#!/usr/bin/env python3

from dealwise.ui.app import DealWiseApplication


def main() -> int:
    app = DealWiseApplication()
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
