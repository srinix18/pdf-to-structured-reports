"""
Re-extract MD&A and/or Letter to Stakeholders for reports missing them.
Only extracts sections that are missing - preserves existing extractions.
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import OUTPUT_DIR, DATA_DIR
from pipeline.section_boundary_detector import SectionBoundaryDetector
from pipeline.section_content_extractor import SectionContentExtractor
from pipeline.extract_text import extract_text
from pipeline.detect_pdf_type import detect_pdf_type
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_reports_missing_sections():
    """Find all reports missing MD&A and/or Letter to Stakeholders"""
    missing = []
    
    for company_dir in OUTPUT_DIR.iterdir():
        if not company_dir.is_dir():
            continue
            
        for year_dir in company_dir.iterdir():
            if not year_dir.is_dir():
                continue
                
            sections_dir = year_dir / "sections"
            mdna_file = sections_dir / "mdna.json"
            letter_file = sections_dir / "letter_to_stakeholders.json"
            report_json = year_dir / "report.json"
            
            # Check if report exists and has sections dir
            if not report_json.exists() or not sections_dir.exists():
                continue
            
            # Check what's missing
            missing_sections = []
            if not mdna_file.exists():
                missing_sections.append("mdna")
            if not letter_file.exists():
                missing_sections.append("letter")
            
            if missing_sections:
                # Find the PDF file in data directory
                company_name = company_dir.name
                data_dir = Path(__file__).parent.parent / "data"
                
                # Search for matching company folder in data dir
                matching_folders = list(data_dir.glob(f"{company_name}*"))
                
                for company_data_dir in matching_folders:
                    if not company_data_dir.is_dir():
                        continue
                    
                    # Find PDFs in this company folder (recursively)
                    pdf_files = list(company_data_dir.glob("**/*.pdf"))
                    for pdf_file in pdf_files:
                        # Check if this PDF matches the year
                        pdf_stem = pdf_file.stem.lower()
                        year_str = year_dir.name
                        
                        # Try different year patterns
                        year_patterns = [
                            f"_{year_str}_",
                            f"_{year_str}-",
                            f"-{year_str}_",
                            f"-{year_str}-",
                        ]
                        
                        # For financial years like 2019_20
                        if year_str.isdigit() and len(year_str) == 4:
                            next_year_short = str(int(year_str) + 1)[2:]
                            year_patterns.extend([
                                f"_{year_str}_{next_year_short}",
                                f"_{year_str}-{next_year_short}",
                                f"-{year_str}_{next_year_short}",
                                f"-{year_str}-{next_year_short}",
                            ])
                        
                        if any(pattern in pdf_stem for pattern in year_patterns):
                            missing.append({
                                "company": company_dir.name,
                                "year": year_dir.name,
                                "pdf_path": pdf_file,
                                "output_dir": year_dir,
                                "missing_sections": missing_sections
                            })
                            break
                    
                    if missing and missing[-1]["company"] == company_name:
                        break
    
    return missing


def reextract_sections_for_report(report_info):
    """
    Re-extract missing sections for a report.
    
    Args:
        report_info: Dict with company, year, pdf_path, output_dir, missing_sections
        
    Returns:
        Dict with extraction results
    """
    company = report_info["company"]
    year = report_info["year"]
    pdf_path = report_info["pdf_path"]
    output_dir = report_info["output_dir"]
    missing = report_info["missing_sections"]
    
    logger.info(f"Re-extracting {', '.join(missing)} for {company} - {year}")
    
    if not pdf_path.exists():
        logger.warning(f"PDF not found: {pdf_path}")
        return {"success": False, "error": "pdf_not_found"}
    
    try:
        # Step 1: Detect PDF type and extract text
        logger.info(f"  Step 1: Detecting PDF type...")
        pdf_type = detect_pdf_type(pdf_path)
        logger.info(f"  PDF type: {pdf_type}")
        
        logger.info(f"  Step 2: Extracting text from PDF...")
        pages, _ = extract_text(pdf_path, pdf_type)
        if not pages:
            logger.error(f"  Failed to extract text from PDF")
            return {"success": False, "error": "text_extraction_failed"}
        
        logger.info(f"  Extracted {len(pages)} pages")
        
        # Step 3: Initialize section boundary detector
        logger.info(f"  Step 3: Detecting section boundaries...")
        detector = SectionBoundaryDetector(pdf_path)
        
        # Extract layout metadata
        detector.extract_layout_metadata()
        
        # Detect section boundaries
        boundaries = detector.detect_section_boundaries()
        
        # Step 4: Initialize section content extractor
        sections_dir = output_dir / "sections"
        sections_dir.mkdir(parents=True, exist_ok=True)
        extractor = SectionContentExtractor(pages, sections_dir)
        
        # Step 5: Extract only missing sections
        logger.info(f"  Step 4: Extracting missing sections...")
        results = {}
        for section_type in missing:
            boundary_key = section_type if section_type == "mdna" else "letter_to_stakeholders"
            boundary = boundaries.get(boundary_key)
            
            if boundary:
                # Extract this section
                section_content = extractor.extract_section(boundary)
                if section_content:
                    # Export section
                    section_file = extractor.export_section(
                        section_content, 
                        company, 
                        year
                    )
                    if section_file:
                        results[section_type] = "extracted"
                        logger.info(f"  ✓ Extracted {section_type}")
                    else:
                        results[section_type] = "failed"
                        logger.warning(f"  ✗ Failed to export {section_type}")
                else:
                    results[section_type] = "failed"
                    logger.warning(f"  ✗ Failed to extract {section_type}")
            else:
                results[section_type] = "not_found"
                logger.info(f"  ✗ {section_type} not found in PDF")
        
        return {"success": True, "results": results}
            
    except Exception as e:
        logger.error(f"Error processing {company} - {year}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def main():
    """Main function to re-extract missing sections"""
    logger.info("=" * 80)
    logger.info("Re-extracting Missing MD&A and Letter to Stakeholders")
    logger.info("=" * 80)
    
    # Find reports with missing sections
    logger.info("Scanning for reports with missing sections...")
    missing_reports = find_reports_missing_sections()
    
    if not missing_reports:
        logger.info("All reports have both MD&A and Letter extracted. Nothing to do.")
        return
    
    # Count what's missing
    mdna_missing = sum(1 for r in missing_reports if "mdna" in r["missing_sections"])
    letter_missing = sum(1 for r in missing_reports if "letter" in r["missing_sections"])
    
    logger.info(f"\nFound:")
    logger.info(f"  Reports missing MD&A: {mdna_missing}")
    logger.info(f"  Reports missing Letter: {letter_missing}")
    logger.info(f"  Total reports to process: {len(missing_reports)}")
    
    # Ask for confirmation
    print(f"\nAbout to re-extract sections for {len(missing_reports)} reports.")
    print("This will only extract sections that are missing.")
    print("Existing extractions will not be affected.")
    response = input("\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        logger.info("Aborted by user.")
        return
    
    # Re-extract
    logger.info("\nStarting re-extraction...")
    stats = {
        "mdna_extracted": 0,
        "mdna_not_found": 0,
        "mdna_failed": 0,
        "letter_extracted": 0,
        "letter_not_found": 0,
        "letter_failed": 0,
        "errors": 0
    }
    
    for i, report_info in enumerate(missing_reports, 1):
        logger.info(f"\n[{i}/{len(missing_reports)}] Processing {report_info['company']} - {report_info['year']}")
        logger.info(f"  Missing: {', '.join(report_info['missing_sections'])}")
        
        try:
            result = reextract_sections_for_report(report_info)
            
            if result["success"]:
                for section_type, status in result["results"].items():
                    stats[f"{section_type}_{status}"] += 1
            else:
                stats["errors"] += 1
                
        except KeyboardInterrupt:
            logger.warning("\nInterrupted by user. Stopping...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            stats["errors"] += 1
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Re-extraction Summary")
    logger.info("=" * 80)
    logger.info(f"Total reports processed: {i}")
    logger.info(f"\nMD&A:")
    logger.info(f"  ✓ Extracted: {stats['mdna_extracted']}")
    logger.info(f"  ✗ Not found: {stats['mdna_not_found']}")
    logger.info(f"  ✗ Failed: {stats['mdna_failed']}")
    logger.info(f"\nLetter to Stakeholders:")
    logger.info(f"  ✓ Extracted: {stats['letter_extracted']}")
    logger.info(f"  ✗ Not found: {stats['letter_not_found']}")
    logger.info(f"  ✗ Failed: {stats['letter_failed']}")
    logger.info(f"\nErrors: {stats['errors']}")
    
    # Calculate new rates
    total_reports = 239  # Current total
    current_mdna = 152
    current_letter = 61
    
    new_mdna = current_mdna + stats['mdna_extracted']
    new_letter = current_letter + stats['letter_extracted']
    
    logger.info(f"\nProjected Extraction Rates:")
    logger.info(f"  MD&A: {new_mdna}/{total_reports} ({new_mdna/total_reports*100:.1f}%) - was {current_mdna/total_reports*100:.1f}%")
    logger.info(f"  Letter: {new_letter}/{total_reports} ({new_letter/total_reports*100:.1f}%) - was {current_letter/total_reports*100:.1f}%")


if __name__ == "__main__":
    main()
