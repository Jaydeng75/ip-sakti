from PIL import Image, ImageDraw, ImageFont

from services.evidence import chunk_pages, extract_document


def test_scanned_pdf_uses_ocr_and_preserves_page_lineage(tmp_path):
    image = Image.new("RGB", (1600, 600), "white")
    drawing = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    drawing.text(
        (80, 120),
        "ZYTHORA OCR evidence: batch identity verified.",
        fill="black",
        font=font,
    )
    path = tmp_path / "scanned-evidence.pdf"
    image.save(path, "PDF", resolution=150)

    pages = extract_document(path, "application/pdf")
    chunks = chunk_pages(pages)

    assert pages[0].extraction_method == "ocr"
    assert "ZYTHORA" in pages[0].text
    assert chunks[0]["page_number"] == 1
