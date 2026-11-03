"""Parse conventional Python tracebacks without executing log content."""

import hashlib
import re
from collections import Counter

START = re.compile(r"^Traceback \(most recent call last\):\s*$")
FRAME = re.compile(r'^\s*File "([^"]+)", line (\d+), in (.+?)\s*$')
EXCEPTION = re.compile(r"^([\w.]+(?:Error|Exception|Warning|Exit|Interrupt|Group)|[\w.]+):(?:\s|$)")
CHAIN = ("During handling of the above exception, another exception occurred:",
         "The above exception was the direct cause of the following exception:")


def parse_tracebacks(text):
    """Yield (exception type, frames) for complete conventional tracebacks."""
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
            frame = FRAME.match(line)
            if frame:
                path, _, func = frame.groups()
                # Keep only the filename, not absolute paths or source line numbers.
                frames.append((path.replace('\\', '/').rsplit('/', 1)[-1], func.strip()))
            elif line and not line[0].isspace():
                match = EXCEPTION.match(line)
                if match and line not in CHAIN:
                    exception_type = match.group(1)
                elif line in CHAIN:
                    exception_type = None
                    frames = []
                elif exception_type is not None:
                    break
            elif not line and exception_type is not None:
                break
            index += 1
        following = index
        while following < len(lines) and not lines[following].strip():
            following += 1
        chained = following < len(lines) and lines[following] in CHAIN
        if exception_type and frames and not chained:
            yield exception_type, tuple(frames)


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
