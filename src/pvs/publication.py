"""Build the PVS site while keeping the reviewed author report private."""
from __future__ import annotations

import hashlib
import json
from urllib.parse import urlencode, quote
import zipfile

from .paths import ROOT

LOCAL_REPORT = 'output/reports/ผลการสำรวจ_20261001.docx'
# Remove the formerly downloadable copy when rebuilding an existing workspace.
LEGACY_REPORT_URL = 'assets/reports/pvs-thailand-study.docx'
REPORT_EMAIL = 'peerasit.sit@mahidol.ac.th'


def prepare_report():
    """Return an email request link; never copy the DOCX into the public site.

    A local author report must still match the reviewed checksum. Public clones
    can use the review record without needing the privately distributed report.
    """
    (ROOT / 'site' / LEGACY_REPORT_URL).unlink(missing_ok=True)
    record = ROOT / 'content/report-release.json'
    if not record.exists():
        return None
    release = json.loads(record.read_text())
    if release.get('status') != 'verified' or release.get('remaining_required_edits') != 0:
        raise ValueError('Report release record still has unresolved review findings.')
    if release.get('delivery') != 'email_request' or release.get('email') != REPORT_EMAIL:
        raise ValueError('The report must be requested through the approved contact email.')
    original = ROOT / LOCAL_REPORT
    if original.exists() and hashlib.sha256(original.read_bytes()).hexdigest() != release['sha256']:
        raise ValueError('Report differs from the reviewed version; rerun the audit before updating the release record.')
    query = urlencode({
        'subject': 'ขอรับรายงานผลการศึกษา People’s Voice Survey ประเทศไทย',
        'body': ('เรียน คุณพีรสิชฌ์ สิทธิรัตน์\r\n\r\n'
                 'ขอรับรายงานผลการศึกษา People’s Voice Survey ประเทศไทยฉบับเต็ม\r\n\r\n'
                 'ชื่อผู้ติดต่อ:\r\nหน่วยงาน (ถ้ามี):\r\nวัตถุประสงค์ในการใช้รายงาน:\r\n\r\n'
                 'ขอบคุณครับ/ค่ะ'),
    }, quote_via=quote)
    return {
        'title': 'รายงานผลการศึกษา People’s Voice Survey ประเทศไทย',
        'description': 'ติดต่อผู้วิเคราะห์ทางอีเมลเพื่อขอรับรายงานผลการศึกษาฉบับเต็ม',
        'status': 'verified',
        'delivery': 'email_request',
        'email': REPORT_EMAIL,
        'request_url': f'mailto:{REPORT_EMAIL}?{query}',
        'sha256': release['sha256'],
    }


def build():
    from . import storytelling

    report = ROOT / LOCAL_REPORT
    source_hash = hashlib.sha256(report.read_bytes()).hexdigest() if report.exists() else None
    report_metadata = prepare_report()
    embedded = set()
    if report.exists():
        with zipfile.ZipFile(report) as document:
            embedded = {hashlib.sha256(document.read(name)).hexdigest()
                        for name in document.namelist()
                        if name.startswith('word/media/') and not name.endswith('/')}
    story = storytelling.build(report_metadata=report_metadata)
    if source_hash and hashlib.sha256(report.read_bytes()).hexdigest() != source_hash:
        raise ValueError('Author report changed during build')
    manifest = {
        'project': 'PVS',
        'status': 'ready_for_publication' if report_metadata else 'dashboard_prepared_report_pending_review',
        'report': None,
        'report_delivery': report_metadata['delivery'] if report_metadata else None,
        'report_request_url': report_metadata['request_url'] if report_metadata else None,
        'local_report': LOCAL_REPORT,
        'report_sha256': report_metadata['sha256'] if report_metadata else source_hash,
        'report_release_record': 'content/report-release.json' if report_metadata else None,
        'source_report_hashes': {str(report.relative_to(ROOT)): source_hash} if source_hash else {},
        'source_reports_unchanged_during_build': True,
        'charts': [{'id': c['id'], 'png': c['png'], 'sha256': c['sha256'],
                    'embedded_unchanged_in_report': c['sha256'] in embedded if report.exists() else None}
                   for c in story['charts']],
        'report_note': (
            'Author corrections rechecked with no remaining findings. The full Thai report is supplied on email request; no DOCX is included in the site or chart bundle. Embedded image checks use the local author report when available.'
            if report_metadata else 'Report request link withheld until a reviewed release record is available.'
        ),
        'data_source': 'Verified national/international aggregates, approved September estimates and rechecked private-user route aggregates',
    }
    (ROOT / 'site/assets/publication-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f"Prepared PVS site: {len(story['chapters'])} chapters in two parts; author report unchanged; report {'available by email request' if report_metadata else 'pending review'}.")
    return ROOT / 'site/index.html'


if __name__ == '__main__':
    build()
