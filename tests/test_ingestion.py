import pytest

from app.ingestion.pdf import (
    Page,
    PDFParseError,
    chunk_pages,
    extract_pages,
    ingest_pdf,
    split_text,
)


# --- extract_pages --------------------------------------------------------


def test_extract_pages_keeps_page_numbers(sample_pdf):
    pages = extract_pages(sample_pdf)

    assert [p.page for p in pages] == [1, 2, 3]
    assert "founded in 2019" in pages[0].text
    assert "Sentence number 39" in pages[1].text


def test_empty_page_is_kept_with_no_text(sample_pdf):
    pages = extract_pages(sample_pdf)

    assert pages[2].text == ""


def test_invalid_pdf_raises_parse_error():
    with pytest.raises(PDFParseError):
        extract_pages(b"this is not a pdf")


# --- split_text -----------------------------------------------------------


def test_short_text_is_one_chunk():
    assert split_text("Just a short page.", chunk_size=500, overlap=100) == [
        "Just a short page."
    ]


def test_empty_text_gives_no_chunks():
    assert split_text("", chunk_size=500, overlap=100) == []


def test_chunks_respect_max_size_and_overlap():
    text = " ".join(f"word{i}" for i in range(300))

    pieces = split_text(text, chunk_size=200, overlap=50)

    assert len(pieces) > 1
    assert all(len(p) <= 200 for p in pieces)
    # The start of each chunk repeats the end of the previous one.
    for previous, current in zip(pieces, pieces[1:]):
        first_word = current.split()[0]
        assert first_word in previous


def test_chunks_do_not_break_words():
    text = " ".join(f"word{i}" for i in range(300))
    words = set(text.split())

    for piece in split_text(text, chunk_size=200, overlap=50):
        assert set(piece.split()) <= words


def test_no_text_is_lost():
    text = " ".join(f"word{i}" for i in range(300))

    joined = " ".join(split_text(text, chunk_size=200, overlap=50))

    assert set(joined.split()) == set(text.split())


def test_prefers_cutting_at_sentence_end():
    text = "A" * 150 + ". " + "b " * 100

    first = split_text(text, chunk_size=200, overlap=20)[0]

    assert first.endswith(".")


def test_turkish_text_is_split_without_damage():
    text = "Şirketin ödeme koşulları ığdır, çağrı ve güneş. " * 20

    pieces = split_text(text, chunk_size=120, overlap=30)

    assert len(pieces) > 1
    assert all("Şirketin" in p or "ödeme" in p or "güneş" in p for p in pieces)


@pytest.mark.parametrize("size, overlap", [(0, 0), (100, 100), (100, -1)])
def test_invalid_settings_are_rejected(size, overlap):
    with pytest.raises(ValueError):
        split_text("some text", chunk_size=size, overlap=overlap)


# --- chunk_pages / ingest_pdf ---------------------------------------------


def test_chunks_carry_metadata_and_stay_on_their_page():
    pages = [Page(page=1, text="First page. " * 60), Page(page=2, text="Second page.")]

    chunks = chunk_pages(pages, doc_id="doc1", filename="a.pdf", chunk_size=200, overlap=50)

    assert {c.page for c in chunks} == {1, 2}
    assert all(c.doc_id == "doc1" and c.filename == "a.pdf" for c in chunks)
    assert all("Second" not in c.text for c in chunks if c.page == 1)
    assert len({c.chunk_id for c in chunks}) == len(chunks)  # ids are unique


def test_ingest_pdf_end_to_end(sample_pdf):
    result = ingest_pdf(sample_pdf, filename="company.pdf", doc_id="abc")

    assert result.doc_id == "abc"
    assert result.page_count == 3
    assert result.empty_pages == [3]
    assert {c.page for c in result.chunks} == {1, 2}
    assert len([c for c in result.chunks if c.page == 2]) > 1  # long page was split
    assert all(c.filename == "company.pdf" for c in result.chunks)


def test_ingest_pdf_generates_doc_id_when_missing(sample_pdf):
    first = ingest_pdf(sample_pdf, filename="a.pdf")
    second = ingest_pdf(sample_pdf, filename="a.pdf")

    assert first.doc_id and first.doc_id != second.doc_id
