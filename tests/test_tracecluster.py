import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tracecluster.core import group_tracebacks

ONE = '''Traceback (most recent call last):
  File "/private/app/main.py", line 12, in start
    go()
  File "/private/app/worker.py", line 42, in go
    raise ValueError('secret')
ValueError: secret
'''
TWO = '''Traceback (most recent call last):
  File "/other/main.py", line 300, in start
    go()
  File "/other/worker.py", line 2, in go
    raise ValueError('different')
ValueError: different
'''


class ParserTests(unittest.TestCase):
    def test_group_normalizes_paths_lines_and_messages(self):
        groups = group_tracebacks(ONE + '\n' + TWO)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['count'], 2)
        self.assertNotIn('secret', str(groups))
        self.assertNotIn('/private', str(groups))

    def test_empty_and_incomplete(self):
        self.assertEqual(group_tracebacks(''), [])
        self.assertEqual(group_tracebacks('Traceback (most recent call last):\n  File "a.py", line 1, in f\n'), [])

    def test_distinct_exception_and_function(self):
        other = ONE.replace('ValueError', 'TypeError')
        self.assertEqual(len(group_tracebacks(ONE + other)), 2)
        self.assertEqual(len(group_tracebacks(ONE + TWO.replace('in go', 'in other'))), 2)

    def test_windows_paths(self):
        self.assertEqual(group_tracebacks(ONE)[0]['fingerprint'],
                         group_tracebacks(ONE.replace('/private/app/', 'C:\\work\\'))[0]['fingerprint'])

    def test_noise(self):
        self.assertEqual(len(group_tracebacks('random noise\n' + ONE + '\nhello')), 1)

    def test_no_frame(self):
        self.assertEqual(group_tracebacks('Traceback (most recent call last):\nValueError: x\n'), [])

    def test_stable_order(self):
        a = group_tracebacks(ONE + ONE.replace('ValueError', 'TypeError'))
        b = group_tracebacks(ONE.replace('ValueError', 'TypeError') + ONE)
        self.assertEqual(a, b)

    def test_chained(self):
        chain = ONE + '\nDuring handling of the above exception, another exception occurred:\n\n' + ONE.replace('ValueError', 'RuntimeError')
        self.assertEqual([g['exception'] for g in group_tracebacks(chain)], ['RuntimeError'])


class CliTests(unittest.TestCase):
    def run_cli(self, *args, input_data=None):
        return subprocess.run([sys.executable, '-m', 'tracecluster', *args], input=input_data,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'log.txt'
            path.write_text(ONE)
            result = self.run_cli(str(path), '--json')
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['total'], 1)

    def test_stdin(self):
        result = self.run_cli('-', '--json', input_data=ONE.encode())
        self.assertEqual(json.loads(result.stdout)['total'], 1)

    def test_limit(self):
        result = self.run_cli('-', '--max-bytes', '2', input_data=ONE.encode())
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b'secret', result.stderr)

    def test_invalid_utf8(self):
        result = self.run_cli('-', input_data=b'\xff')
        self.assertEqual(result.returncode, 2)

    def test_missing_file_hides_path(self):
        result = self.run_cli('/tmp/private-token-123')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b'private-token', result.stderr)

    def test_zero_limit(self):
        self.assertNotEqual(self.run_cli('-', '--max-bytes', '0').returncode, 0)

    def test_text(self):
        result = self.run_cli('-', input_data=ONE.encode())
        self.assertEqual(result.returncode, 0)
        self.assertIn(b'ValueError', result.stdout)


if __name__ == '__main__':
    unittest.main()
