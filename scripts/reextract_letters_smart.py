"""
Re-extract letters, processing smaller PDFs first to avoid hanging on large files.
"""
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.section_boundary_detector import SectionBoundaryDetector
from pipeline.section_content_extractor import SectionContentExtractor
from pipeline.section_metadata import SectionType
from pipeline.extract_text import extract_text
from pipeline.detect_pdf_type import detect_pdf_type
from config.config import OUTPUT_DIR, LOGS_DIR

# Data directory is at project root, not in config
DATA_DIR = Path(__file__).parent.parent / "data"

# Setup logging
log_file = LOGS_DIR / f"reextract_letters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)


def find_reports_without_letters() -> List[tuple]:
    """Find all reports without letters, sorted by PDF size (smallest first)"""
    reports_needing_letters = []
    
    for company_dir in OUTPUT_DIR.iterdir():
        if not company_dir.is_dir():
            continue
        
        for year_dir in company_dir.iterdir():
            if not year_dir.is_dir():
                continue
            
            # Check if letter already exists
            sections_dir = year_dir / "sections"
            letter_json = sections_dir / "letter_to_stakeholders.json"
            
            if letter_json.exists():
                continue  # Already has letter
            
            # Check if report.json exists
            report_json = year_dir / "report.json"
            if not report_json.exists():
                continue
            
            # Find corresponding PDF
            company_name = company_dir.name
            year = year_dir.name
            
            # Search in data directory for matching company folder
            for company_folder in DATA_DIR.iterdir():
                if not company_folder.is_dir():
                    continue
                
                if company_name.lower() in company_folder.name.lower():
                    # Find PDFs with matching year
                    for pdf_path in company_folder.rglob("*.pdf"):
                        if year in pdf_path.stem or year.replace("20", "") in pdf_path.stem:
                            # Get file size
                            size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
                            reports_needing_letters.append((company_name, year, year_dir, pdf_path, size_mb))
                            break
                    break
    
    # Sort by size (smallest first to avoid hangs)
    reports_needing_letters.sort(key=lambda x: x[4])
    
    return reports_needing_letters


def reextract_letter(company_name: str, year: str, output_dir: Path, pdf_path: Path, size_mb: float) -> bool:
    """Re-extract letter using PDF layout analysis - same method as main pipeline"""
    logger.info(f"\n{'='*80}")
    logger.info(f"Re-extracting letter for: {company_name} / {year}")
    logger.info(f"PDF: {pdf_path.name} ({size_mb:.1f} MB)")
    logger.info(f"{'='*80}")
    
    # Skip extremely large PDFs (>100MB) to avoid memory issues
    if size_mb > 100:
        logger.warning(f"  [SKIP] Very large PDF ({size_mb:.1f} MB) - may cause memory issues")
        return False
    
    try:
        # Step 1: Detect PDF type and extract text (same as main.py)
        logger.info("Step 1: Detecting PDF type and extracting text...")
        pdf_type, _ = detect_pdf_type(pdf_path)
        logger.info(f"  PDF type: {pdf_type}")
        
        # Skip scanned PDFs that require OCR
        if pdf_type == "scanned":
            logger.warning(f"  [SKIP] Scanned PDF - requires OCR (Tesseract not configured)")
            return False
        
        pages, extraction_stats = extract_text(pdf_path, pdf_type)
        if not pages:
            logger.error("  [FAIL] No text extracted from PDF")
            return False
        
        logger.info(f"  Extracted {len(pages)} pages ({extraction_stats['extraction_coverage']:.1f}% coverage)")
        
        # Step 2: Use boundary detector to find letter section
        logger.info("Step 2: Detecting letter boundary from PDF layout...")
        detector = SectionBoundaryDetector(pdf_path)
        detector.extract_layout_metadata()
        boundaries = detector.detect_section_boundaries()
        
        letter_boundary = boundaries.get("letter_to_stakeholders")
        
        if not letter_boundary:
            logger.info("  [SKIP] Letter section not detected in PDF")
            return False
        
        logger.info(f"  [OK] Letter found: pages {letter_boundary.start_page}-{letter_boundary.end_page}, "
                   f"confidence={letter_boundary.confidence:.2f}")
        logger.info(f"  Heading: '{letter_boundary.start_heading}'")
        
        # Step 3: Extract letter content (same as main.py)
        logger.info("Step 3: Extracting letter content...")
        sections_dir = output_dir / "sections"
        sections_dir.mkdir(exist_ok=True)
        
        extractor = SectionContentExtractor(pages, sections_dir)
        letter_content = extractor.extract_section(letter_boundary)
        
        if not letter_content:
            logger.warning("  [FAIL] Failed to extract letter content")
            return False
        
        logger.info(f"  [OK] Extracted {letter_content.character_count:,} characters "
                   f"across {letter_content.page_count} pages")
        
        # Step 4: Export to both JSON and DOCX (same as main.py)
        logger.info("Step 4: Exporting files...")
        
        # Export to DOCX
        docx_path = extractor.export_section_to_docx(letter_content, company_name, year)
        logger.info(f"  [OK] Created: {docx_path.name}")
        
        # Export to JSON (section_content_extractor does this automatically)
        json_path = sections_dir / "letter_to_stakeholders.json"
        logger.info(f"  [OK] Created: {json_path.name}")
        
        # Step 5: Update metadata
        logger.info("Step 5: Updating sections_metadata.json...")
        metadata_path = sections_dir / "sections_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            metadata = {}
        
        metadata["letter_to_stakeholders"] = {
            "boundary": {
                "section_type": letter_boundary.section_type.value,
                "start_page": letter_boundary.start_page,
                "end_page": letter_boundary.end_page,
                "confidence": letter_boundary.confidence,
                "start_heading": letter_boundary.start_heading,
                "detection_method": letter_boundary.detection_method
            },
            "content_stats": {
                "section_type": letter_content.section_type.value,
                "start_page": letter_content.start_page,
                "end_page": letter_content.end_page,
                "character_count": letter_content.character_count,
                "page_count": letter_content.page_count
            },
            "extracted": True,
            "extraction_date": datetime.now().isoformat()
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[SUCCESS] Re-extracted letter for {company_name} / {year}")
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Error re-extracting letter: {e}", exc_info=True)
        return False


def main():
    logger.info("="*80)
    logger.info("Letter Re-extraction Script (Smart - Small PDFs First)")
    logger.info("="*80)
    
    # Find reports without letters
    logger.info("\nScanning for reports without letters...")
    reports = find_reports_without_letters()
    
    logger.info(f"\nFound {len(reports)} reports without letters")
    
    # Show size distribution
    small = sum(1 for r in reports if r[4] <= 10)
    medium = sum(1 for r in reports if 10 < r[4] <= 20)
    large = sum(1 for r in reports if r[4] > 20)
    
    logger.info(f"\nSize distribution:")
    logger.info(f"  Small (<=10 MB): {small}")
    logger.info(f"  Medium (10-20 MB): {medium}")
    logger.info(f"  Large (>20 MB): {large}")
    
    # Filter to only large files (>20MB)
    reports = [r for r in reports if r[4] > 20]
    
    if not reports:
        logger.info("No large reports to process!")
        return
    
    # Ask for confirmation
    print(f"\nWill process ONLY {len(reports)} LARGE reports (>20 MB)")
    response = input("Continue? (y/n): ").strip().lower()
    
    if response != 'y':
        logger.info("Aborted by user")
        return
    
    # Process each report
    results = {
        "success": [],
        "not_found": [],
        "skipped_large": []
    }
    
    for i, (company_name, year, output_dir, pdf_path, size_mb) in enumerate(reports, 1):
        logger.info(f"\nProcessing {i}/{len(reports)}")
        
        success = reextract_letter(company_name, year, output_dir, pdf_path, size_mb)
        
        if success:
            results["success"].append((company_name, year))
        else:
            results["not_found"].append((company_name, year))
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("RE-EXTRACTION SUMMARY")
    logger.info("="*80)
    logger.info(f"Total reports scanned: {len(reports)}")
    logger.info(f"Successfully extracted letters: {len(results['success'])}")
    logger.info(f"Letters not found in PDF: {len(results['not_found'])}")
    logger.info(f"Skipped (large PDFs): {len(results['skipped_large'])}")
    
    if results['success']:
        logger.info("\nSuccessfully extracted:")
        for company, year in results['success'][:10]:
            logger.info(f"  [OK] {company} / {year}")
        if len(results['success']) > 10:
            logger.info(f"  ... and {len(results['success']) - 10} more")
    
    logger.info(f"\nLog saved to: {log_file}")


if __name__ == "__main__":
    main()
