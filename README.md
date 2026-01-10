# PDF to DOCX Converter

Automated Python pipeline to convert annual report PDFs into clean, readable DOCX files with proper layout preservation.

## Features

- **Automatic PDF Type Detection**: Distinguishes between text-based and scanned PDFs
- **OCR Support**: Automatically applies OCR to scanned PDFs using Tesseract
- **Smart Column Detection**: Dynamically handles any number of pages per PDF page (1, 2, 3+), each with their own column structure
- **Section Extraction**: Automatically detects and extracts MD&A and Letter to Stakeholders sections
- **Layout Preservation**: Maintains proper reading order (left-to-right, top-to-bottom)
- **Page-by-Page Organization**: Structured DOCX output with clear page separators
- **Comprehensive Metrics**: Detailed quality analysis and extraction statistics
- **Batch Processing**: Process multiple companies and years efficiently

## Installation

### Prerequisites

- Python 3.12+
- Tesseract OCR (for scanned PDFs)

### Setup

1. Clone the repository:

```bash
git clone https://github.com/srinix18/pdf-to-structured-reports.git
cd pdf-to-structured-reports
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Install Tesseract OCR:
   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - Update `TESSERACT_CMD` path in `config.py` if needed

## Usage

### Single PDF Processing

```bash
python test_single.py
```

### Batch Processing

```bash
python main.py
```

Place PDFs in the `data/` folder with structure:

```
data/
  Company Name/
    company_name_year.pdf
```

## Output

Generated files in `outputs/` folder:

```
outputs/
  Company Name/
    year/
      report.docx       # Clean, formatted document
      metadata.json     # Processing statistics
```

## How It Works

1. **PDF Detection**: Identifies if PDF contains text or requires OCR
2. **Text Extraction**: Extracts text with smart column detection
   - Detects multiple pages per PDF page (common in annual reports)
   - Identifies column structure within each page
   - Maintains proper reading order
3. **Text Cleaning**: Conservative cleaning that preserves layout
4. **DOCX Export**: Generates structured document with page-by-page organization

## Configuration

Edit `config.py` to customize:

- OCR resolution (DPI)
- Input/output directories
- Tesseract path
- Minimum text length thresholds

## Architecture

```
project/
├── pipeline/          # Core processing modules
│   ├── detect_pdf_type.py
│   ├── extract_text.py
│   ├── clean_text.py
│   ├── export_outputs.py
│   ├── section_boundary_detector.py
│   ├── section_content_extractor.py
│   └── section_metadata.py
├── tests/            # Test and validation scripts
│   ├── test_single.py
│   ├── test_section_extraction.py
│   ├── compare_pdf_docx.py
│   └── debug_headings.py
├── config/           # Configuration settings
│   └── config.py
├── main.py          # Main orchestrator for batch processing
├── data/            # Input PDF files
├── outputs/         # Generated DOCX files
└── logs/            # Processing logs
```

### Core Modules:

- `main.py` - Main orchestrator for batch processing
- `pipeline/` - Core extraction and processing modules
- `tests/` - Testing and validation scripts
- `config/` - Configuration settings

## Requirements

- pdfplumber - PDF text extraction
- PyMuPDF (fitz) - Fallback PDF processing
- pytesseract - OCR interface
- Pillow - Image processing for OCR
- python-docx - DOCX file generation
- pandas - Data handling

## License

MIT
