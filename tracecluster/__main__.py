"""Command-line interface."""

import argparse
import json
import sys
from pathlib import Path

from .core import group_tracebacks


def main(argv=None):
    parser = argparse.ArgumentParser(description='Group repeated Python tracebacks in a log.')
    parser.add_argument('path', help='UTF-8 log file, or - for standard input')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    parser.add_argument('--max-bytes', type=int, default=8_000_000, help='Maximum input size (default: 8000000)')
    args = parser.parse_args(argv)
    if args.max_bytes < 1:
        parser.error('--max-bytes must be positive')
    try:
        if args.path == '-':
            raw = sys.stdin.buffer.read(args.max_bytes + 1)
        else:
            with Path(args.path).open('rb') as source:
                raw = source.read(args.max_bytes + 1)
        if len(raw) > args.max_bytes:
            raise ValueError('input exceeds --max-bytes')
        groups = group_tracebacks(raw.decode('utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        # Do not echo paths or raw log content in diagnostics.
        if isinstance(exc, ValueError) and str(exc) == 'input exceeds --max-bytes':
            message = str(exc)
        elif isinstance(exc, UnicodeError):
            message = 'input must be UTF-8'
        else:
            message = 'cannot read input'
        print('tracecluster: ' + message, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({'groups': groups, 'total': sum(g['count'] for g in groups)}, ensure_ascii=True))
    else:
        for group in groups:
            print(f"{group['count']:>5}  {group['fingerprint']}  {group['exception']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
