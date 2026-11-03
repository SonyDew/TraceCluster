import unittest
from tracecluster.core import group_tracebacks


def tb(error='ValueError: redacted', path='/srv/secret/app.py', fn='run'):
    return f'Traceback (most recent call last):\n  File "{path}", line 9, in {fn}\n    fail()\n{error}\n'


class EveningTests(unittest.TestCase):
    def test_chained(self):
        s = tb() + '\nDuring handling of the above exception, another exception occurred:\n\n' + tb('TypeError: x')
        self.assertEqual([(g['exception'], g['count']) for g in group_tracebacks(s)], [('TypeError', 1)])

    def test_consecutive(self):
        self.assertEqual(group_tracebacks(tb() + tb())[0]['count'], 2)

    def test_indented_note(self):
        self.assertEqual(group_tracebacks(tb() + '    note: secret\n' + tb())[0]['count'], 2)

    def test_no_frame(self):
        self.assertEqual(group_tracebacks('Traceback (most recent call last):\nValueError: x\n'), [])

    def test_incomplete_chain(self):
        s = tb() + '\nDuring handling of the above exception, another exception occurred:\n'
        self.assertEqual(group_tracebacks(s)[0]['exception'], 'ValueError')

    def test_no_leak(self):
        self.assertNotIn('secret', str(group_tracebacks(tb())))

    def test_bare(self):
        self.assertEqual(group_tracebacks(tb('KeyboardInterrupt'))[0]['exception'], 'KeyboardInterrupt')

    def test_distinct(self):
        self.assertEqual(len(group_tracebacks(tb(fn='a') + tb(fn='b'))), 2)

    def test_log_boundary(self):
        self.assertEqual(group_tracebacks(tb() + 'INFO: next request\n')[0]['exception'], 'ValueError')

    def test_log_after_incomplete_traceback(self):
        s = 'Traceback (most recent call last):\n  File "a.py", line 1, in run\nINFO: next request\n'
        self.assertEqual(group_tracebacks(s), [])
