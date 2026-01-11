"""
Delete outputs for reports missing sections and create list for reprocessing.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import OUTPUT_DIR
import logging
import shutil

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 80)
    logger.info("Finding Reports with Missing Sections")
    logger.info("=" * 80)
    
    incomplete_reports = []
    
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
                    missing.append("MD&A")
                if letter_missing:
                    missing.append("Letter")
                
                incomplete_reports.append({
                    "company": company_dir.name,
                    "year": year_dir.name,
                    "year_dir": year_dir,
                    "missing": missing
                })
    
    if not incomplete_reports:
        logger.info("No incomplete reports found!")
        return
    
    logger.info(f"\nFound {len(incomplete_reports)} reports with missing sections:")
    mdna_count = sum(1 for r in incomplete_reports if "MD&A" in r['missing'])
    letter_count = sum(1 for r in incomplete_reports if "Letter" in r['missing'])
    logger.info(f"  Missing MD&A: {mdna_count}")
    logger.info(f"  Missing Letter: {letter_count}")
    
    logger.info("\nSample:")
    for r in incomplete_reports[:10]:
        logger.info(f"  {r['company']} - {r['year']}: missing {', '.join(r['missing'])}")
    
    print(f"\n⚠️  This will DELETE the output folders for {len(incomplete_reports)} incomplete reports")
    print("so they can be reprocessed with the full pipeline.")
    response = input("\nProceed with deletion? (y/n): ")
    
    if response.lower() != 'y':
        logger.info("Aborted.")
        return
    
    logger.info("\nDeleting incomplete report folders...")
    deleted = 0
    
    for report in incomplete_reports:
        try:
            shutil.rmtree(report['year_dir'])
            deleted += 1
            logger.info(f"  ✓ Deleted: {report['company']}/{report['year']}")
        except Exception as e:
            logger.error(f"  ✗ Error deleting {report['company']}/{report['year']}: {e}")
    
    logger.info(f"\n✅ Deleted {deleted} incomplete report folders")
    logger.info("\nNext step: Run the batch processing script to reprocess these PDFs:")
    logger.info("  python scripts/run_batch_v2.py")


if __name__ == "__main__":
    main()
