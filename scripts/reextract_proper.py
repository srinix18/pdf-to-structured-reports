"""
Re-run original pipeline on reports with missing or low-quality sections.
Uses the proper PDF-based extraction with layout analysis.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import OUTPUT_DIR
import logging

# DATA_DIR is one level up from project root
DATA_DIR = Path(__file__).parent.parent / "data"

from main import process_single_pdf

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_reports_needing_reextraction():
    """Find reports with missing or low-quality section extractions"""
    to_reextract = []
    
    for company_dir in OUTPUT_DIR.iterdir():
        if not company_dir.is_dir():
            continue
            
        for year_dir in company_dir.iterdir():
            if not year_dir.is_dir():
                continue
                
            sections_dir = year_dir / "sections"
            if not sections_dir.exists():
                continue
            
            needs_reextraction = False
            reasons = []
            
            # Check both section types
            for section_name in ["mdna", "letter_to_stakeholders"]:
                json_file = sections_dir / f"{section_name}.json"
                
                if not json_file.exists():
                    reasons.append(f"missing_{section_name}")
                    needs_reextraction = True
                else:
                    # Check if it's a low-quality extraction
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Check for DOCX-based extractions (likely low quality)
                        if data.get('extraction_method') == 'docx_keyword_matching':
                            char_count = data.get('character_count', 0)
                            if char_count < 2000:  # Suspiciously short
                                reasons.append(f"low_quality_{section_name}_{char_count}chars")
                                needs_reextraction = True
                    except Exception as e:
                        logger.error(f"Error reading {json_file}: {e}")
            
            if needs_reextraction:
                # Find corresponding PDF
                company_name = company_dir.name
                year = year_dir.name
                
                # Search for PDF in data directory
                pdf_found = None
                for data_company_dir in DATA_DIR.iterdir():
                    if not data_company_dir.is_dir():
                        continue
                    if company_name.lower() in data_company_dir.name.lower():
                        for pdf_file in data_company_dir.glob(f"**/*{year}*.pdf"):
                            pdf_found = pdf_file
                            break
                    if pdf_found:
                        break
                
                if pdf_found:
                    to_reextract.append({
                        "company": company_name,
                        "year": year,
                        "pdf_path": pdf_found,
                        "output_dir": company_dir / year,
                        "reasons": reasons
                    })
    
    return to_reextract


def main():
    logger.info("=" * 80)
    logger.info("Re-extracting Sections Using Original Pipeline")
    logger.info("=" * 80)
    
    logger.info("Scanning for reports needing re-extraction...")
    reports = find_reports_needing_reextraction()
    
    if not reports:
        logger.info("No reports need re-extraction.")
        return
    
    # Group by reason
    missing = [r for r in reports if any('missing' in reason for reason in r['reasons'])]
    low_quality = [r for r in reports if any('low_quality' in reason for reason in r['reasons'])]
    
    logger.info(f"\nFound {len(reports)} reports needing re-extraction:")
    logger.info(f"  Missing sections: {len(missing)}")
    logger.info(f"  Low quality extractions: {len(low_quality)}")
    
    # Show some examples
    if low_quality:
        logger.info(f"\nExamples of low-quality extractions:")
        for r in low_quality[:5]:
            logger.info(f"  {r['company']} - {r['year']}: {', '.join(r['reasons'])}")
    
    response = input(f"\nRe-run pipeline on these {len(reports)} reports? (y/n): ")
    if response.lower() != 'y':
        logger.info("Aborted by user.")
        return
    
    logger.info("\nRe-running pipeline...")
    success = 0
    errors = 0
    
    for i, report in enumerate(reports, 1):
        logger.info(f"\n[{i}/{len(reports)}] {report['company']} - {report['year']}")
        logger.info(f"  Reasons: {', '.join(report['reasons'])}")
        
        try:
            # Run original pipeline
            result = process_single_pdf(
                pdf_path=report['pdf_path'],
                company_name=report['company'],
                year=report['year']
            )
            
            if result['success']:
                logger.info(f"  ✓ Successfully re-extracted")
                success += 1
            else:
                logger.error(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                errors += 1
        except Exception as e:
            logger.error(f"  ✗ Error: {e}", exc_info=True)
            errors += 1
    
    logger.info("\n" + "=" * 80)
    logger.info(f"Summary:")
    logger.info(f"  ✓ Success: {success}")
    logger.info(f"  ✗ Errors: {errors}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
