# Pipeline Modules

Core processing modules for PDF-to-DOCX extraction and section detection.

## Modules:

### Text Extraction

- **detect_pdf_type.py** - Detects if PDF is text-based or scanned
- **extract_text.py** - Extracts text with dynamic column detection
- **clean_text.py** - Cleans extracted text while preserving layout

### Output Generation

- **export_outputs.py** - Exports to DOCX format with page-by-page structure

### Section Extraction

- **section_metadata.py** - Data structures for section boundaries
- **section_boundary_detector.py** - Detects MD&A and Letter to Stakeholders using PDF layout
- **section_content_extractor.py** - Extracts section content and creates separate DOCX files

### Utilities

- **utils.py** - Helper functions
