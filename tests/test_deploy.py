import os
import unittest
from unittest.mock import patch

from services.tmdb.deploy import safe_diagnostic, run


class DeployDiagnosticsTests(unittest.TestCase):
    def test_preserves_error_without_credentials(self):
        with patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'secret-token',
                                    'CLOUDFLARE_ACCOUNT_ID': 'account-id',
                                    'TMDB_READ_TOKEN': 'tmdb-secret'}):
            message = safe_diagnostic('\x1b[31mError 10000: permission denied\x1b[0m '
                                      'secret-token account-id tmdb-secret Bearer other-token')
        self.assertIn('Error 10000: permission denied', message)
        for hidden in ('secret-token', 'account-id', 'tmdb-secret', 'other-token', '\x1b'):
            self.assertNotIn(hidden, message)

    def test_cli_failure_is_sanitized(self):
        result = type('Result', (), {'returncode': 1, 'stdout': '',
                                    'stderr': 'permission denied: secret-token'})()
        with patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'secret-token'}), \
                patch('services.tmdb.deploy.subprocess.run', return_value=result):
            with self.assertRaises(SystemExit) as caught:
                run(['deploy'])
        self.assertIn('permission denied', str(caught.exception))
        self.assertNotIn('secret-token', str(caught.exception))
