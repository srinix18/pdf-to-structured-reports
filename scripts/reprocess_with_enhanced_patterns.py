"""
Re-process reports with missing sections using the enhanced patterns.
Deletes incomplete outputs and re-runs the full PDF pipeline.
"""
import sys
from pathlib import Path
import shutil
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import OUTPUT_DIR
from main import process_single_pdf
import logging

# Correct DATA_DIR - it's at project root, not in config
DATA_DIR = Path(__file__).parent.parent / "data"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_pdf_for_report(company_name, year):
    """Find the PDF file for a given company and year"""
    # Extract company name without number prefix
    # E.g., "(1) 360 ONE WAM LTD" -> "360 ONE WAM LTD"
    match = re.match(r'\(\d+\)\s*(.+)', company_name)
    if match:
        clean_company_name = match.group(1).strip()
    else:
        clean_company_name = company_name
    
    # Search for matching company folder in data directory
    # Data folders have format like: "(1) 360 ONE WAM LTD.-20251230T101729Z-1-001"
    for data_folder in DATA_DIR.iterdir():
        if not data_folder.is_dir():
            continue
        
        # Check if this folder matches the company
        if clean_company_name.upper() in data_folder.name.upper():
            # Search for PDF with matching year
            pdf_files = list(data_folder.rglob(f"*{year}*.pdf"))
            if pdf_files:
                return pdf_files[0]
    
    return None


def find_incomplete_reports():
    """Find all reports with missing MD&A or Letter sections"""
    incomplete = []
    
    for company_dir in OUTPUT_DIR.iterdir():
        if not company_dir.is_dir():
            continue
        
        for year_dir in company_dir.iterdir():
            if not year_dir.is_dir():
                continue
            
            sections_dir = year_dir / "sections"
            if not sections_dir.exists():
                continue
            
            mdna_missing = not (sections_dir / "mdna.json").exists()
            letter_missing = not (sections_dir / "letter_to_stakeholders.json").exists()
            
            if mdna_missing or letter_missing:
                missing = []
                if mdna_missing:
                    missing.append("mdna")
                if letter_missing:
                    missing.append("letter")
                
                incomplete.append({
                    "company": company_dir.name,
                    "year": year_dir.name,
                    "year_dir": year_dir,
                    "missing": missing
                })
    
    return incomplete


def main():
    logger.info("=" * 80)
    logger.info("Re-processing Reports with Enhanced Patterns")
    logger.info("=" * 80)
    
    # Find incomplete reports
    logger.info("Scanning for reports with missing sections...")
    incomplete_reports = find_incomplete_reports()
    
    if not incomplete_reports:
        logger.info("No reports with missing sections found!")
        return
    
    mdna_missing = sum(1 for r in incomplete_reports if "mdna" in r['missing'])
    letter_missing = sum(1 for r in incomplete_reports if "letter" in r['missing'])
    
    logger.info(f"\nFound {len(incomplete_reports)} reports with missing sections:")
    logger.info(f"  Missing MD&A: {mdna_missing}")
    logger.info(f"  Missing Letter: {letter_missing}")
    
    # Match to PDFs
    logger.info("\nMatching reports to PDF files...")
    reports_to_process = []
    not_found = []
    
    for report in incomplete_reports:
        pdf_path = find_pdf_for_report(report['company'], report['year'])
        if pdf_path:
            reports_to_process.append({
                **report,
                'pdf_path': pdf_path
            })
        else:
            not_found.append(f"{report['company']} - {report['year']}")
    
    logger.info(f"  ✓ Found PDFs for {len(reports_to_process)} reports")
    if not_found:
        logger.warning(f"  ⚠ Could not find PDFs for {len(not_found)} reports")
        logger.info("\nSample not found:")
        for nf in not_found[:5]:
            logger.info(f"    - {nf}")
    
    if not reports_to_process:
        logger.error("No PDFs found to process!")
        return
    
    # Show samples
    logger.info("\nSample reports to reprocess:")
    for r in reports_to_process[:10]:
        logger.info(f"  {r['company']} - {r['year']}: missing {', '.join(r['missing'])}")
    
    print(f"\nWARNING: This will:")
    print(f"  1. DELETE output folders for {len(reports_to_process)} incomplete reports")
    print(f"  2. Re-run the FULL PIPELINE with enhanced patterns")
    print(f"  3. Process {len(reports_to_process)} PDF files")
    response = input("\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        logger.info("Aborted by user.")
        return
    
    # Delete incomplete outputs
    logger.info("\n" + "=" * 80)
    logger.info("Step 1: Deleting incomplete outputs...")
    logger.info("=" * 80)
    
    deleted = 0
    for report in reports_to_process:
        try:
            shutil.rmtree(report['year_dir'])
            deleted += 1
            logger.info(f"  ✓ Deleted: {report['company']}/{report['year']}")
        except Exception as e:
            logger.error(f"  ✗ Error: {report['company']}/{report['year']}: {e}")
    
    logger.info(f"\n✅ Deleted {deleted} incomplete output folders")
    
    # Re-process PDFs
    logger.info("\n" + "=" * 80)
    logger.info("Step 2: Re-processing PDFs with enhanced patterns...")
    logger.info("=" * 80)
    
    success = 0
    errors = 0
    
    for i, report in enumerate(reports_to_process, 1):
        logger.info(f"\n[{i}/{len(reports_to_process)}] Processing {report['company']} - {report['year']}")
        logger.info(f"  PDF: {report['pdf_path'].name}")
        
        try:
            result = process_single_pdf(report['pdf_path'])
            
            if result and result.get('status') == 'success':
                success += 1
                
                # Check what got extracted
                output_dir = OUTPUT_DIR / report['company'] / report['year'] / "sections"
                extracted = []
                if (output_dir / "mdna.json").exists():
                    extracted.append("MD&A")
                if (output_dir / "letter_to_stakeholders.json").exists():
                    extracted.append("Letter")
                
                if extracted:
                    logger.info(f"  ✓ Success - Extracted: {', '.join(extracted)}")
                else:
                    logger.info(f"  ✓ Processed but no sections extracted")
            else:
                errors += 1
                error_msg = result.get('error', 'Unknown error') if result else 'No result'
                logger.warning(f"  ✗ Failed: {error_msg}")
                
        except Exception as e:
            errors += 1
            logger.error(f"  ✗ Error: {e}")
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Reports processed: {len(reports_to_process)}")
    logger.info(f"  ✓ Success: {success}")
    logger.info(f"  ✗ Errors: {errors}")
    
    # Check new extraction counts
    mdna_count = 0
    letter_count = 0
    for company_dir in OUTPUT_DIR.iterdir():
        if not company_dir.is_dir():
            continue
        for year_dir in company_dir.iterdir():
            if not year_dir.is_dir():
                continue
            sections_dir = year_dir / "sections"
            if sections_dir.exists():
                if (sections_dir / "mdna.json").exists():
                    mdna_count += 1
                if (sections_dir / "letter_to_stakeholders.json").exists():
                    letter_count += 1
    
    logger.info(f"\nNew extraction counts:")
    logger.info(f"  MD&A: {mdna_count}/239 ({mdna_count/239*100:.1f}%)")
    logger.info(f"  Letter: {letter_count}/239 ({letter_count/239*100:.1f}%)")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
