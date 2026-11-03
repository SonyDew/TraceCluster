"""Group conventional Python tracebacks without executing log content."""

import hashlib
import re
from collections import Counter

START = 'Traceback (most recent call last):'
FRAME = re.compile(r'^\s*File "([^"]+)", line (\d+), in (.+?)\s*$')
EXCEPTION = re.compile(r'^([A-Za-z_][\w.]*)\s*:(?:\s|$)')
LOG_LEVELS = frozenset({'DEBUG', 'INFO', 'WARNING', 'WARN', 'ERROR', 'CRITICAL', 'TRACE'})
BARE = frozenset({'KeyboardInterrupt', 'SystemExit', 'GeneratorExit'})
CHAIN = frozenset({
    'During handling of the above exception, another exception occurred:',
    'The above exception was the direct cause of the following exception:',
})


def _next_start(lines, index):
    while index < len(lines) and not lines[index].strip():
        index += 1
    return index if index < len(lines) and lines[index] == START else None


def parse_tracebacks(text):
    """Yield complete traceback signatures, keeping the final chained exception."""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if lines[index] != START:
            index += 1
            continue
        index += 1
        frames = []
        exception = None
        while index < len(lines):
            line = lines[index]
            if line == START:
                break
            match = FRAME.fullmatch(line)
            if match:
                path, _, func = match.groups()
                frames.append((path.replace('\\', '/').rsplit('/', 1)[-1], func.strip()))
                index += 1
                continue
            if not line or line[0].isspace():
                index += 1
                continue
            if frames:
                match = EXCEPTION.match(line)
                if match and match.group(1) not in LOG_LEVELS:
                    exception = match.group(1)
                    index += 1
                elif line in BARE:
                    exception = line
                    index += 1
            break

        if exception and frames:
            # A chain separator suppresses this signature only when another
            # conventional traceback immediately follows it.
            look = index
            chained = False
            while look < len(lines):
                line = lines[look]
                if line in CHAIN:
                    following = _next_start(lines, look + 1)
                    if following is not None:
                        index = following
                        chained = True
                    break
                if line == START or (line and not line[0].isspace()):
                    break
                look += 1
            if chained:
                continue
            yield exception, tuple(frames)
        if index < len(lines) and lines[index] != START:
            index += 1


def group_tracebacks(text):
    """Return groups ordered by descending count and fingerprint."""
    counts = Counter(parse_tracebacks(text))
    groups = []
    for (exception, frames), count in counts.items():
        signature = exception + '\n' + '\n'.join(f'{name}:{func}' for name, func in frames)
        fingerprint = hashlib.sha256(signature.encode('utf-8')).hexdigest()[:16]
        groups.append({'fingerprint': fingerprint, 'exception': exception,
                       'frames': [{'file': name, 'function': func} for name, func in frames],
                       'count': count})
    return sorted(groups, key=lambda g: (-g['count'], g['fingerprint']))
