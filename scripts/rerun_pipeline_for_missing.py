"""
Re-run the original PDF pipeline for reports with missing MD&A or Letter sections.
Uses the full pipeline logic with PDF analysis, not simple keyword matching.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import OUTPUT_DIR, DATA_DIR
from main import process_single_pdf
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_pdfs_for_missing_sections():
    """Find PDFs that need re-processing due to missing sections"""
    to_process = []
    
    for company_dir in OUTPUT_DIR.iterdir():
        if not company_dir.is_dir():
            continue
        
        company_name = company_dir.name
        
        for year_dir in company_dir.iterdir():
            if not year_dir.is_dir():
                continue
                
            year = year_dir.name
            sections_dir = year_dir / "sections"
            
            # Check what's missing
            if not sections_dir.exists():
                continue
                
            mdna_missing = not (sections_dir / "mdna.json").exists()
            letter_missing = not (sections_dir / "letter_to_stakeholders.json").exists()
            
            if mdna_missing or letter_missing:
                # Find the original PDF in data directory
                # Company folder names in data dir have different format
                company_data_folders = list(DATA_DIR.glob(f"*{company_name.split(')')[1].strip()}*"))
                
                if company_data_folders:
                    # Look for PDF with matching year
                    for data_folder in company_data_folders:
                        pdf_files = list(data_folder.glob(f"**/*{year}*.pdf"))
                        if pdf_files:
                            to_process.append({
                                "company": company_name,
                                "year": year,
                                "pdf_path": pdf_files[0],
                                "missing": {
                                    "mdna": mdna_missing,
                                    "letter": letter_missing
                                }
                            })
                            break
    
    return to_process


def main():
    logger.info("=" * 80)
    logger.info("Re-running Pipeline for Reports with Missing Sections")
    logger.info("=" * 80)
    
    # Find reports to process
    logger.info("Scanning for reports with missing sections...")
    reports = find_pdfs_for_missing_sections()
    
    if not reports:
        logger.info("No reports found with missing sections!")
        return
    
    mdna_missing = sum(1 for r in reports if r['missing']['mdna'])
    letter_missing = sum(1 for r in reports if r['missing']['letter'])
    
    logger.info(f"\nFound {len(reports)} reports to re-process:")
    logger.info(f"  Missing MD&A: {mdna_missing}")
    logger.info(f"  Missing Letter: {letter_missing}")
    
    # Show sample
    logger.info("\nSample reports:")
    for r in reports[:5]:
        missing_str = ", ".join([k for k, v in r['missing'].items() if v])
        logger.info(f"  {r['company']} - {r['year']}: missing {missing_str}")
    
    response = input(f"\nRe-process these {len(reports)} PDFs with full pipeline? (y/n): ")
    if response.lower() != 'y':
        logger.info("Aborted by user.")
        return
    
    logger.info("\nStarting re-processing...")
    logger.info("This will use the FULL PDF pipeline with proper extraction logic.\n")
    
    success = 0
    errors = 0
    
    for i, report in enumerate(reports, 1):
        logger.info(f"[{i}/{len(reports)}] Processing {report['company']} - {report['year']}")
        
        try:
            # Use the original process_single_pdf function
            result = process_single_pdf(report['pdf_path'])
            
            if result and result.get('status') == 'success':
                success += 1
                logger.info(f"  ✓ Success")
            else:
                errors += 1
                logger.warning(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            errors += 1
            logger.error(f"  ✗ Error: {e}")
    
    logger.info("\n" + "=" * 80)
    logger.info("Summary:")
    logger.info(f"  ✓ Success: {success}")
    logger.info(f"  ✗ Errors: {errors}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
