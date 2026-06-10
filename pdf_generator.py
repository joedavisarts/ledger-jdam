import base64
import io
import json
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates', 'pdf')
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'assets')


def _logo_b64_for_file(filename: str) -> str:
    if not filename:
        return ''
    path = os.path.join(ASSETS_DIR, filename)
    if not os.path.exists(path):
        return ''
    with open(path, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()


def _format_currency(value):
    try:
        return '{:,.2f}'.format(float(value))
    except (ValueError, TypeError):
        return '0.00'


def _format_date(value, fmt='%B %d, %Y'):
    if not value:
        return ''
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').strftime(fmt)
    except Exception:
        return str(value)


def _nl2br(s):
    if not s:
        return ''
    return str(s).replace('\n', '<br>')


def generate_pdf(doc: dict, client: dict, user: dict) -> bytes:
    doc_type = doc['doc_type']
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    env.filters['format_date'] = _format_date
    env.filters['format_currency'] = _format_currency
    env.filters['nl2br'] = _nl2br

    template = env.get_template(f'{doc_type}.html')

    # Parse JSON fields so templates get lists, not raw strings
    user_ctx = dict(user)
    user_ctx['payment_methods'] = json.loads(user.get('payment_methods_json') or '[]')
    user_ctx['social_links'] = json.loads(user.get('social_links_json') or '[]')

    html_str = template.render(
        doc=doc,
        client=client,
        logo_b64=_logo_b64_for_file(user.get('logo_filename')),
        logotype_b64=_logo_b64_for_file(user.get('logotype_filename')),
        user=user_ctx,
    )

    pdf_bytes = io.BytesIO()
    HTML(string=html_str, base_url=ASSETS_DIR).write_pdf(pdf_bytes)
    return pdf_bytes.getvalue()
