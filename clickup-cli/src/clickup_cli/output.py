"""JSON output formatting.

All output goes to stdout — errors included — so agents can parse a single stream.
"""

import json
import sys


def output(data: object, pretty: bool = False) -> None:
    indent = 2 if pretty else None
    json.dump(data, sys.stdout, indent=indent, default=str)
    sys.stdout.write("\n")


def output_error(message: str, pretty: bool = False) -> None:
    output({"error": message}, pretty=pretty)
