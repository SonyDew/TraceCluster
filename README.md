# TraceCluster

**Day 8 of the SonyDev GitHub Marathon (November 3, 2026). Status: In Development.**

TraceCluster groups conventional Python tracebacks from UTF-8 log files. A group is identified by the exception class and ordered stack frames (filename and function name). Absolute directories, line numbers, source snippets, and exception messages do not affect the fingerprint and are not printed.

## Usage

Requires Python 3.10 or later. No runtime dependencies.

```sh
python -m pip install .
tracecluster application.log
tracecluster application.log --json
cat application.log | tracecluster - --json
python -m unittest discover -s tests -v
```

The JSON output includes `total` and `groups`; each group contains `fingerprint`, `exception`, `frames`, and `count`.

Exit status: `0` for successfully processed input (including no tracebacks), `2` for invalid arguments, unreadable, oversized, or non-UTF-8 input. The default input limit is 8,000,000 bytes; change it with `--max-bytes`.

## Limitations

- Parses conventional `Traceback (most recent call last):` text, not arbitrary log formats or structured exception JSON.
- Ignores incomplete tracebacks and tracebacks without recognized frames.
- Chained exceptions are represented by the final traceback when the standard chain separator and a subsequent traceback are present.
- Filename-only normalization can merge unrelated modules with the same basename and function names.
- Exception messages and source code are discarded. Filenames and function names may still contain sensitive identifiers.
- Reads bounded input into memory; does not stream very large logs.
- Python 3.11+ ExceptionGroup tree formatting and log lines with prefixes are not supported.

## Development report — afternoon

On Linux with Python 3.13.5, the 15 existing tests and 14 new boundary/CLI tests passed using `python -m unittest discover -s tests -q`. The audit fixed exception classification when a log record or exception note follows a traceback, added bare `KeyboardInterrupt` handling, and prevented CLI argument errors from echoing supplied values. No source log files are modified. Windows and Python 3.10–3.12 have not been tested in this audit. No stable release is claimed.
