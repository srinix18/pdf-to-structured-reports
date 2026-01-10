# Test Scripts

Test and validation scripts for the PDF extraction pipeline.

## Scripts:

- **test_single.py** - Process a single PDF file (quick test)
- **test_section_extraction.py** - Test MD&A and Letter extraction with detailed output
- **compare_pdf_docx.py** - Validates extraction accuracy by comparing PDF vs DOCX character counts
- **debug_headings.py** - Debug tool to analyze PDF headings for section detection tuning

## Usage:

Run from project root:

```bash
python tests/test_single.py
python tests/test_section_extraction.py
python tests/compare_pdf_docx.py
```
