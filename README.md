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

Exit status: `0` for successfully processed input (including no tracebacks), `2` for unreadable, oversized, or non-UTF-8 input. The default input limit is 8,000,000 bytes; change it with `--max-bytes`.

## Limitations

- Parses conventional `Traceback (most recent call last):` text, not arbitrary log formats or structured exception JSON.
- Ignores incomplete tracebacks and tracebacks without recognized frames.
- Chained exceptions are represented by the final traceback when the standard chain separator is present.
- Filename-only normalization can merge unrelated modules with the same basename and function names.
- Exception messages and source code are discarded. Filenames and function names may still contain sensitive identifiers.
- Reads bounded input into memory; does not stream very large logs.

## Development report — morning

On Linux with Python 3.13, 15 unit and CLI tests passed using `python -m unittest discover -s tests -q`. Windows and Python 3.10–3.12 have not been tested. The installed console script has not been separately tested.
