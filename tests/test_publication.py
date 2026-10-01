"""The verified report is requested by email and never copied into the site."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from pvs import publication


class ReportReleaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.patch = patch.object(publication, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.content = b'reviewed report bytes'
        self.record = self.root / 'content/report-release.json'
        self.record.parent.mkdir(parents=True)
        self.record.write_text(json.dumps({
            'status': 'verified', 'remaining_required_edits': 0,
            'delivery': 'email_request', 'email': publication.REPORT_EMAIL,
            'sha256': hashlib.sha256(self.content).hexdigest(),
        }))
        self.public = self.root / 'site' / publication.LEGACY_REPORT_URL
        self.public.parent.mkdir(parents=True)
        self.public.write_bytes(self.content)

    def test_public_clone_removes_stale_copy_and_offers_email_without_private_docx(self):
        metadata = publication.prepare_report()
        self.assertFalse(self.public.exists())
        self.assertNotIn('url', metadata)
        self.assertEqual(metadata['delivery'], 'email_request')
        request = urlsplit(metadata['request_url'])
        self.assertEqual(request.scheme, 'mailto')
        self.assertEqual(request.path, publication.REPORT_EMAIL)
        message = parse_qs(request.query)
        self.assertIn('ขอรับรายงาน', message['subject'][0])
        self.assertIn('ฉบับเต็ม', message['body'][0])

    def test_reviewed_local_report_is_preserved_and_never_copied(self):
        original = self.root / publication.LOCAL_REPORT
        original.parent.mkdir(parents=True)
        original.write_bytes(self.content)
        metadata = publication.prepare_report()
        self.assertEqual(original.read_bytes(), self.content)
        self.assertEqual(metadata['sha256'], hashlib.sha256(self.content).hexdigest())
        self.assertFalse(self.public.exists())

    def test_changed_author_report_fails_and_removes_old_public_copy(self):
        original = self.root / publication.LOCAL_REPORT
        original.parent.mkdir(parents=True)
        original.write_bytes(b'new unreviewed edits')
        with self.assertRaisesRegex(ValueError, 'differs from the reviewed version'):
            publication.prepare_report()
        self.assertFalse(self.public.exists())
        self.assertEqual(original.read_bytes(), b'new unreviewed edits')

    def test_unresolved_review_cannot_enable_request(self):
        record = json.loads(self.record.read_text())
        record['remaining_required_edits'] = 1
        self.record.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'unresolved review findings'):
            publication.prepare_report()
        self.assertFalse(self.public.exists())

    def test_delivery_record_cannot_silently_restore_direct_download(self):
        record = json.loads(self.record.read_text())
        record['delivery'] = 'download'
        self.record.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'approved contact email'):
            publication.prepare_report()
        self.assertFalse(self.public.exists())


if __name__ == '__main__':
    unittest.main()
