"""
Batch processing script for running the pipeline on a subset of companies.
"""
import sys
import logging
from pathlib import Path
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import process_single_pdf, setup_logging
from config.config import LOGS_DIR
import json

# Get correct data directory (workspace level)
DATA_DIR = Path(__file__).parent.parent / "data"


def main():
    """Process first N companies from the data directory."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch process PDFs for N companies")
    parser.add_argument("--companies", type=int, default=50, help="Number of companies to process (default: 50)")
    parser.add_argument("--start", type=int, default=0, help="Starting company index (default: 0)")
    args = parser.parse_args()
    
    # Setup logging
    log_file = LOGS_DIR / f"batch_process_{args.companies}companies.log"
    setup_logging(log_file)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting batch processing for companies {args.start} to {args.start + args.companies}")
    logger.info(f"Data directory: {DATA_DIR}")
    
    # Get company folders
    all_companies = sorted(list(DATA_DIR.glob("*")), key=lambda x: x.name)
    all_companies = [c for c in all_companies if c.is_dir()]
    
    # Slice to get requested range
    companies_to_process = all_companies[args.start:args.start + args.companies]
    
    logger.info(f"Found {len(all_companies)} total companies")
    logger.info(f"Processing {len(companies_to_process)} companies")
    
    if not companies_to_process:
        logger.error("No companies found in range")
        return
    
    # Collect all PDFs from selected companies
    pdf_files = []
    for company_dir in companies_to_process:
        pdfs = list(company_dir.rglob("*.pdf"))
        pdf_files.extend(pdfs)
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    if not pdf_files:
        logger.error("No PDF files found")
        return
    
    # Process each PDF
    results = []
    
    for pdf_path in tqdm(pdf_files, desc="Processing PDFs", unit="file"):
        result = process_single_pdf(pdf_path)
        results.append(result)
    
    # Generate summary
    logger.info("\n" + "="*80)
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info("="*80)
    
    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    
    logger.info(f"Companies processed: {len(companies_to_process)}")
    logger.info(f"Total PDFs processed: {len(results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    
    if failed > 0:
        logger.info("\nFailed files:")
        for r in results:
            if r["status"] == "failed":
                logger.info(f"  - {r['pdf_path']}: {r.get('error', 'Unknown error')}")
    
    # Save summary report
    summary_path = LOGS_DIR / f"batch_summary_{args.companies}companies.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSummary report saved to: {summary_path}")
    
    logger.info("\nBatch processing completed!")


if __name__ == "__main__":
    main()
