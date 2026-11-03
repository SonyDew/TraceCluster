"""Parse conventional Python tracebacks without executing log content."""

import hashlib
import re
from collections import Counter

START = re.compile(r"^Traceback \(most recent call last\):$")
FRAME = re.compile(r'^\s*File "([^"]+)", line (\d+), in (.+?)\s*$')
EXCEPTION = re.compile(r"^([A-Za-z_][\w.]*) (?::(?:\s|$))", re.X)
BARE_EXCEPTIONS = frozenset({'KeyboardInterrupt', 'SystemExit', 'GeneratorExit'})
CHAIN = frozenset({
    'During handling of the above exception, another exception occurred:',
    'The above exception was the direct cause of the following exception:',
})


def parse_tracebacks(text):
    """Yield signatures from complete conventional traceback blocks."""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if not START.fullmatch(lines[index]):
            index += 1
            continue
        index += 1
        frames = []
        exception_type = None
        while index < len(lines):
            line = lines[index]
            if START.fullmatch(line):
                break
            frame = FRAME.fullmatch(line)
            if frame:
                path, _, func = frame.groups()
                frames.append((path.replace('\\', '/').rsplit('/', 1)[-1], func.strip()))
            elif line and not line[0].isspace():
                match = EXCEPTION.match(line)
                if match:
                    exception_type = match.group(1)
                    index += 1
                    break
                if line in BARE_EXCEPTIONS:
                    exception_type = line
                    index += 1
                    break
                # A log boundary or malformed traceback is not an exception.
                break
            index += 1

        # Continuation lines and exception notes do not change the exception type.
        # A standard chain marker suppresses the preceding traceback only when
        # another traceback actually follows it.
        following = index
        while following < len(lines) and not START.fullmatch(lines[following]):
            if lines[following] in CHAIN:
                next_line = following + 1
                while next_line < len(lines) and not lines[next_line].strip():
                    next_line += 1
                if next_line < len(lines) and START.fullmatch(lines[next_line]):
                    exception_type = None
                    index = next_line
                break
            if lines[following] and not lines[following][0].isspace():
                # Unrelated log lines are not part of a traceback.
                break
            following += 1
        if exception_type and frames:
            yield exception_type, tuple(frames)
        if index <= following and index < len(lines) and not START.fullmatch(lines[index]):
            index += 1


def group_tracebacks(text):
    """Return stable groups ordered by frequency then fingerprint."""
    counts = Counter(parse_tracebacks(text))
    groups = []
    for (exception, frames), count in counts.items():
        signature = exception + '\n' + '\n'.join(f'{name}:{func}' for name, func in frames)
        fingerprint = hashlib.sha256(signature.encode('utf-8')).hexdigest()[:16]
        groups.append({'fingerprint': fingerprint, 'exception': exception,
                       'frames': [{'file': name, 'function': func} for name, func in frames],
                       'count': count})
    return sorted(groups, key=lambda g: (-g['count'], g['fingerprint']))
