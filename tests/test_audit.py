"""Regression tests for traceback boundaries and CLI diagnostics."""

import json
import subprocess
import sys
import unittest

from tracecluster.core import group_tracebacks

ONE = '''Traceback (most recent call last):
  File "/private/app/main.py", line 12, in start
    go()
  File "/private/app/worker.py", line 42, in go
    raise ValueError('secret')
ValueError: secret
'''
TWO = ONE.replace('ValueError: secret', 'TypeError: different')


class BoundaryTests(unittest.TestCase):
    def test_log_line_does_not_replace_exception(self):
        self.assertEqual(group_tracebacks(ONE + 'INFO: next request\n')[0]['exception'], 'ValueError')

    def test_exception_note_does_not_replace_exception(self):
        groups = group_tracebacks(ONE + 'Note: private context\n')
        self.assertEqual(groups[0]['exception'], 'ValueError')
        self.assertNotIn('private context', str(groups))

    def test_bare_keyboard_interrupt(self):
        self.assertEqual(group_tracebacks(ONE.replace('ValueError: secret', 'KeyboardInterrupt'))[0]['exception'],
                         'KeyboardInterrupt')

    def test_direct_cause_chain(self):
        text = ONE + '\nThe above exception was the direct cause of the following exception:\n\n' + TWO
        self.assertEqual([g['exception'] for g in group_tracebacks(text)], ['TypeError'])

    def test_chain_without_second_traceback(self):
        text = ONE + '\nDuring handling of the above exception, another exception occurred:\n'
        self.assertEqual(group_tracebacks(text)[0]['exception'], 'ValueError')

    def test_adjacent_tracebacks(self):
        self.assertEqual(group_tracebacks(ONE + ONE)[0]['count'], 2)

    def test_distinct_files_same_function(self):
        self.assertEqual(len(group_tracebacks(ONE + ONE.replace('worker.py', 'handler.py'))), 2)

    def test_multiline_message_not_used(self):
        text = ONE + '    private note\n'
        self.assertEqual(group_tracebacks(text)[0]['fingerprint'], group_tracebacks(ONE)[0]['fingerprint'])

    def test_custom_exception_class(self):
        text = ONE.replace('ValueError: secret', 'myapp.Failure: secret')
        self.assertEqual(group_tracebacks(text)[0]['exception'], 'myapp.Failure')

    def test_truncated_after_frame(self):
        self.assertEqual(group_tracebacks('Traceback (most recent call last):\n  File "x.py", line 3, in f\n'), [])


class ArgumentTests(unittest.TestCase):
    def run_cli(self, *args, data=None):
        return subprocess.run([sys.executable, '-m', 'tracecluster', *args],
                              input=data, capture_output=True, check=False)

    def test_invalid_numeric_argument_hides_value(self):
        result = self.run_cli('-', '--max-bytes', 'secret-token-123')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b'secret-token-123', result.stderr)

    def test_unknown_argument_hides_value(self):
        result = self.run_cli('-', '--secret-token-123')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b'secret-token-123', result.stderr)

    def test_empty_input(self):
        result = self.run_cli('-', '--json', data=b'')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {'groups': [], 'total': 0})

    def test_exact_input_limit(self):
        result = self.run_cli('-', '--json', '--max-bytes', str(len(ONE.encode())), data=ONE.encode())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['total'], 1)
