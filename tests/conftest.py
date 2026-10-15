"""Shared pytest fixtures.

Fake LLM and fake embedding classes will live here so tests never need
network access or an API key.
"""

import textwrap

import pytest


def build_pdf(pages: list[str]) -> bytes:
    """Build a tiny valid PDF with one text page per string.

    An empty string gives a page with no text, like a scanned image page.
    Only plain ASCII is supported (the built-in Helvetica font has no
    Turkish letters); Turkish text is tested at the chunking level instead.
    """
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)  # PDF object numbers start at 1

    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pages_id = len(objects) + 1 + 2 * len(pages)  # reserve its number for last
    page_ids = []
    for text in pages:
        lines = textwrap.wrap(text, 80) or []
        ops = ["BT", "/F1 11 Tf", "14 TL", "50 780 Td"]
        for line in lines:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            ops.append(f"({escaped}) Tj T*")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1")
        content_id = add(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
        page_ids.append(
            add(
                b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] "
                b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
                % (pages_id, font_id, content_id)
            )
        )
    kids = b" ".join(b"%d 0 R" % i for i in page_ids)
    assert add(b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(pages))) == pages_id
    catalog_id = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref_at = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        catalog_id,
        xref_at,
    )
    return bytes(out)


@pytest.fixture
def sample_pdf() -> bytes:
    """Three pages: short text, long text, and an empty (scanned-like) page."""
    long_text = " ".join(
        f"Sentence number {i} talks about invoices and payment terms." for i in range(40)
    )
    return build_pdf(
        [
            "The company was founded in 2019 in Istanbul.",
            long_text,
            "",
        ]
    )
