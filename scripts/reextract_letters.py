"""
Re-extract letter_to_stakeholders for reports that don't have them yet.
Uses the EXACT same pipeline method as main.py - not a gimmick.
"""
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.section_boundary_detector import SectionBoundaryDetector
from pipeline.section_content_extractor import SectionContentExtractor
from pipeline.section_metadata import SectionType
from pipeline.extract_text import PageText
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
    """
    Find all reports that have MD&A but no letter_to_stakeholders.
    
    Returns:
        List of tuples: (company_name, year, output_dir, pdf_path)
    """
    reports_needing_letters = []
    
    for company_dir in OUTPUT_DIR.iterdir():
        if not company_dir.is_dir():
            continue
        
        for year_dir in company_dir.iterdir():
            if not year_dir.is_dir():
                continue
            
            # Check if report exists
            report_json = year_dir / "report.json"
            if not report_json.exists():
                continue
            
            # Check if letter already exists
            sections_dir = year_dir / "sections"
            letter_json = sections_dir / "letter_to_stakeholders.json"
            
            if letter_json.exists():
                continue  # Already has letter
            
            # Find corresponding PDF
            company_name = company_dir.name
            year = year_dir.name
            
            pdf_path = find_pdf_for_report(company_name, year)
            if pdf_path:
                reports_needing_letters.append((company_name, year, year_dir, pdf_path))
            else:
                logger.warning(f"PDF not found for {company_name} / {year}")
    
    return reports_needing_letters


def find_pdf_for_report(company_name: str, year: str) -> Optional[Path]:
    """
    Find the PDF file corresponding to a report.
    
    Args:
        company_name: Company name from output directory
        year: Year from output directory
        
    Returns:
        Path to PDF file or None if not found
    """
    # Search in data directory for matching company folder
    for company_folder in DATA_DIR.iterdir():
        if not company_folder.is_dir():
            continue
        
        # Match company name (handle variations)
        if company_name.lower() in company_folder.name.lower():
            # Find PDFs with matching year
            for pdf_path in company_folder.rglob("*.pdf"):
                if year in pdf_path.stem or year.replace("20", "") in pdf_path.stem:
                    return pdf_path
    
    return None


def load_pages_from_report(report_json_path: Path) -> List[PageText]:
    """
    Reconstruct PageText objects from report.json.
    
    Args:
        report_json_path: Path to report.json
        
    Returns:
        List of PageText objects
    """
    with open(report_json_path, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    pages = []
    
    # Extract text from hierarchical structure
    if 'structure' in report_data:
        page_texts = {}  # page_num -> text content
        
        def extract_content_from_structure(structure_item, current_page):
            """Recursively extract content from structure"""
            texts = []
            
            # Get heading
            if 'heading' in structure_item:
                texts.append(structure_item['heading'])
            
            # Get content
            if 'content' in structure_item:
                if isinstance(structure_item['content'], list):
                    texts.extend(structure_item['content'])
                elif isinstance(structure_item['content'], str):
                    texts.append(structure_item['content'])
            
            # Process subsections
            if 'subsections' in structure_item:
                for subsection in structure_item['subsections']:
                    texts.extend(extract_content_from_structure(subsection, current_page))
            
            return texts
        
        # Process all structure items
        for item in report_data['structure']:
            content_parts = extract_content_from_structure(item, report_data.get('start_page', 1))
            content = '\n\n'.join(content_parts)
            
            # We don't have exact page boundaries from structure, so create single "page"
            # This is OK because boundary detector uses PDF directly
            pages.append(PageText(
                page_number=report_data.get('start_page', 1),
                text=content,
                char_count=len(content),
                extraction_method='from_report_json'
            ))
    
    return pages


def reextract_letter(company_name: str, year: str, output_dir: Path, pdf_path: Path) -> bool:
    """
    Re-extract letter_to_stakeholders using the exact same method as main pipeline.
    
    Args:
        company_name: Company name
        year: Report year
        output_dir: Output directory for this report
        pdf_path: Path to PDF file
        
    Returns:
        True if letter was found and extracted, False otherwise
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Re-extracting letter for: {company_name} / {year}")
    logger.info(f"PDF: {pdf_path.name}")
    logger.info(f"{'='*80}")
    
    try:
        # Step 1: Use boundary detector to find letter section
        logger.info("Step 1: Detecting letter boundary from PDF layout...")
        detector = SectionBoundaryDetector(pdf_path)
        detector.extract_layout_metadata()
        boundaries = detector.detect_section_boundaries()
        
        letter_boundary = boundaries.get("letter_to_stakeholders")
        
        if not letter_boundary:
            logger.info("  ✗ Letter section not detected in PDF")
            return False
        
        logger.info(f"  ✓ Letter found: pages {letter_boundary.start_page}-{letter_boundary.end_page}, "
                   f"confidence={letter_boundary.confidence:.2f}")
        logger.info(f"  Heading: '{letter_boundary.start_heading}'")
        
        # Step 2: Load pages from report.json (for text content)
        logger.info("Step 2: Loading page text from report.json...")
        report_json = output_dir / "report.json"
        pages = load_pages_from_report(report_json)
        logger.info(f"  Loaded {len(pages)} pages")
        
        # Step 3: Extract letter content using boundary
        logger.info("Step 3: Extracting letter content...")
        sections_dir = output_dir / "sections"
        sections_dir.mkdir(exist_ok=True)
        
        extractor = SectionContentExtractor(pages, sections_dir)
        letter_content = extractor.extract_section(letter_boundary)
        
        if not letter_content:
            logger.warning("  ✗ Failed to extract letter content")
            return False
        
        logger.info(f"  ✓ Extracted {letter_content.character_count:,} characters "
                   f"across {letter_content.page_count} pages")
        
        # Step 4: Export letter to DOCX and JSON
        logger.info("Step 4: Exporting letter files...")
        docx_path = extractor.export_section_to_docx(letter_content, company_name, year)
        logger.info(f"  ✓ Created: {docx_path.name}")
        logger.info(f"  ✓ Created: letter_to_stakeholders.json")
        
        # Step 5: Update sections_metadata.json
        logger.info("Step 5: Updating sections_metadata.json...")
        metadata_path = sections_dir / "sections_metadata.json"
        
        # Load existing metadata
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            metadata = {}
        
        # Update letter section
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
        
        logger.info(f"  ✓ Updated sections_metadata.json")
        logger.info(f"✓ Successfully re-extracted letter for {company_name} / {year}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error re-extracting letter: {e}", exc_info=True)
        return False


def main():
    """Main entry point"""
    logger.info("="*80)
    logger.info("Letter Re-extraction Script")
    logger.info("Using EXACT same pipeline method as main.py")
    logger.info("="*80)
    
    # Find reports without letters
    logger.info("\nScanning for reports without letters...")
    reports = find_reports_without_letters()
    
    logger.info(f"\nFound {len(reports)} reports without letters")
    
    if not reports:
        logger.info("All reports already have letters extracted!")
        return
    
    # Ask for confirmation
    print(f"\nWill attempt to re-extract letters for {len(reports)} reports.")
    response = input("Continue? (y/n): ").strip().lower()
    
    if response != 'y':
        logger.info("Aborted by user")
        return
    
    # Process each report
    results = {
        "success": [],
        "failed": [],
        "not_found": []
    }
    
    for i, (company_name, year, output_dir, pdf_path) in enumerate(reports, 1):
        logger.info(f"\nProcessing {i}/{len(reports)}")
        
        success = reextract_letter(company_name, year, output_dir, pdf_path)
        
        if success:
            results["success"].append((company_name, year))
        else:
            results["not_found"].append((company_name, year))
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("RE-EXTRACTION SUMMARY")
    logger.info("="*80)
    logger.info(f"Total reports processed: {len(reports)}")
    logger.info(f"Successfully extracted letters: {len(results['success'])}")
    logger.info(f"Letters not found in PDF: {len(results['not_found'])}")
    
    if results['success']:
        logger.info("\nSuccessfully extracted:")
        for company, year in results['success'][:10]:
            logger.info(f"  ✓ {company} / {year}")
        if len(results['success']) > 10:
            logger.info(f"  ... and {len(results['success']) - 10} more")
    
    if results['not_found']:
        logger.info("\nNot found in PDF:")
        for company, year in results['not_found'][:10]:
            logger.info(f"  ✗ {company} / {year}")
        if len(results['not_found']) > 10:
            logger.info(f"  ... and {len(results['not_found']) - 10} more")
    
    logger.info(f"\nLog saved to: {log_file}")


if __name__ == "__main__":
    main()
