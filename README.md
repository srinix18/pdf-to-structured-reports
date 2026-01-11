# PDF to DOCX Converter

Automated Python pipeline to convert annual report PDFs into clean, readable DOCX files with proper layout preservation.

## Features

- **Automatic PDF Type Detection**: Distinguishes between text-based and scanned PDFs
- **OCR Support**: Automatically applies OCR to scanned PDFs using Tesseract
- **Smart Column Detection**: Dynamically handles any number of pages per PDF page (1, 2, 3+), each with their own column structure
- **Section Extraction**: Automatically detects and extracts MD&A and Letter to Stakeholders sections
- **Hierarchical JSON Output**: Full report and sections exported with detected headings and nested structure
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
      report.docx                        # Clean, formatted full report
      report.json                        # Full report with hierarchical structure
      metadata.json                      # Processing statistics and quality metrics
      sections/
        mdna.docx                        # MD&A section with heading styles
        mdna.json                        # MD&A hierarchical JSON structure
        letter_to_stakeholders.docx      # Letter section with heading styles
        letter_to_stakeholders.json      # Letter hierarchical JSON structure
        sections_metadata.json           # Section boundaries and confidence scores
```

### JSON Structure

Both the full report and individual sections are exported as hierarchical JSON with detected headings:

```json
{
  "company": "Company Name",
  "year": "2019",
  "section": "Annual Report",
  "start_page": 1,
  "end_page": 142,
  "confidence": 1.0,
  "structure": [
    {
      "heading": "Financial Review",
      "level": 2,
      "content": ["paragraph 1...", "paragraph 2..."],
      "subsections": [
        {
          "heading": "Revenue Analysis",
          "level": 3,
          "content": ["..."]
        }
      ]
    }
  ],
  "metadata": {
    "total_headings": 241,
    "heading_levels": [1, 2, 3],
    "character_count": 859845,
    "paragraph_count": 532
  }
}
```

## How It Works

1. **PDF Detection**: Identifies if PDF contains text or requires OCR
2. **Text Extraction**: Extracts text with smart column detection
   - Detects multiple pages per PDF page (common in annual reports)
   - Identifies column structure within each page
   - Maintains proper reading order
3. **Text Cleaning**: Conservative cleaning that preserves layout
4. **Section Extraction**: Automatic boundary detection for MD&A and Letter to Stakeholders
   - **Layout Analysis**: Extracts PDF text blocks with position, font size, and formatting metadata
   - **Keyword-Based Detection**: Matches 123 letter patterns and 71 MD&A patterns
   - **Multi-Stage Validation**:
     - Stage 1: Exact keyword matching with position scoring
     - Stage 2: Partial matching with configurable thresholds
     - Stage 3: Fuzzy matching for variations and OCR errors
   - **Context-Aware Rules**: Different heuristics per section type
     - Letters: First 20 pages, font ≥1.05x median, or lines <50 chars
     - MD&A: Top 40% of page (y<350), font ≥1.1x median (stricter)
   - **Section End Detection**:
     - Financial statement keywords (balance sheet, cash flow, etc.)
     - New section transitions (wealth creation, financial highlights, etc.)
     - Structural markers (board report, directors report, annexures)
     - Prominent headings (≥1.5x-1.8x median font size)
     - Length limits (25 pages max for letters)
   - **Confidence Scoring**: Multi-factor scoring (0.0-1.0) based on:
     - Keyword match strength (exact vs. fuzzy)
     - Font size prominence
     - Position on page
     - Surrounding context
5. **Hierarchy Building**: Detects headings using deterministic heuristics
   - Uppercase headings (Level 1)
   - Title case headings (Level 2)
   - Keyword matching (MD&A, Letter to Stakeholders topics)
   - Structural cues (short lines, colons, numeric prefixes)
6. **Export**: Generates both DOCX and hierarchical JSON
   - DOCX with proper heading styles (Heading 1, 2, 3)
   - JSON with nested structure for NLP/analytics

### Section Extraction Performance

| Section Type               | Initial            | Enhanced Patterns  | Smart Re-extraction       | Final Rate | Method                                                                                    |
| -------------------------- | ------------------ | ------------------ | ------------------------- | ---------- | ----------------------------------------------------------------------------------------- |
| **Letter to Stakeholders** | 58/104<br>(55.8%)  | 58/104<br>(55.8%)  | **87/104**<br>**(83.7%)** | **83.7%**  | Layout analysis + 123 keyword patterns + context-aware detection + multi-stage validation |
| **MD&A**                   | 101/104<br>(97.1%) | 101/104<br>(97.1%) | 101/104<br>(97.1%)        | **97.1%**  | Layout analysis + 71 keyword patterns + strict position rules                             |

**Key Improvements:**

- **Letter Extraction**: +27.9 percentage points (55.8% → 83.7%)
  - Enhanced section end detection with prominent heading recognition
  - Added 52 new letter keyword patterns (71 → 123)
  - Context-aware font size thresholds (≥1.05x median)
  - Multi-factor confidence scoring
- **Processing Capability**:
  - Handles PDFs from 90 to 600+ pages
  - Processes files up to 50MB efficiently
  - Skips extremely large files (>100MB) to avoid memory issues
- **Smart Re-extraction**:
  - Sorted by file size (small → large) for optimal processing
  - Extracted 29 additional letters from previously failed reports
  - Successfully processed large PDFs (21-50 MB)

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
│   ├── section_hierarchy_builder.py
│   ├── section_metadata.py
│   └── utils.py
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
