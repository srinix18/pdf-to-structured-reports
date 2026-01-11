"""
Batch process PDFs from companies numbered 1-50, with idempotency and error handling.
"""
import sys
from pathlib import Path
import re
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import process_single_pdf
from config.config import LOGS_DIR

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"


def extract_number_from_company_name(company_name: str) -> int:
    """Extract the leading number from company folder name like '(10) Company Name'"""
    match = re.match(r'\((\d+)\)', company_name)
    if match:
        return int(match.group(1))
    return 999999  # Put unnumbered companies at the end


def get_processed_companies():
    """Get set of companies that have been fully processed (have at least one report.json)"""
    outputs_dir = Path(__file__).parent.parent / "config" / "outputs"
    if not outputs_dir.exists():
        return set()
    
    processed = set()
    for company_dir in outputs_dir.iterdir():
        if company_dir.is_dir():
            # Check if any year subdirectory has report.json
            has_reports = False
            for year_dir in company_dir.iterdir():
                if year_dir.is_dir() and (year_dir / "report.json").exists():
                    has_reports = True
                    break
            if has_reports:
                processed.add(company_dir.name)
    
    return processed


def main():
    """Process first 50 companies (by number prefix), focusing on 15 unprocessed ones"""
    
    # Get all company directories
    all_companies = [d for d in DATA_DIR.iterdir() if d.is_dir()]
    
    # Sort by number prefix
    all_companies_sorted = sorted(all_companies, key=lambda d: extract_number_from_company_name(d.name))
    
    # Get first 50 by number
    companies_1_to_50 = []
    for company in all_companies_sorted:
        num = extract_number_from_company_name(company.name)
        if 1 <= num <= 50:
            companies_1_to_50.append(company)
    
    print(f"Found {len(companies_1_to_50)} companies numbered 1-50")
    
    # Get processed companies
    processed = get_processed_companies()
    print(f"Already processed: {len(processed)} companies")
    
    # Find unprocessed companies
    unprocessed = [c for c in companies_1_to_50 if c.name not in processed]
    print(f"Unprocessed: {len(unprocessed)} companies")
    
    # Limit to 15 unprocessed companies
    companies_to_process = unprocessed[:15]
    print(f"\nWill process {len(companies_to_process)} companies")
    
    # Collect all PDFs from selected companies (recursively)
    pdf_files = []
    for company_dir in companies_to_process:
        pdfs = list(company_dir.rglob("*.pdf"))  # Recursive glob
        pdf_files.extend(pdfs)
    
    print(f"Total PDFs to process: {len(pdf_files)}")
    
    # Process PDFs with progress bar
    results = {
        "success": [],
        "failed": [],
        "skipped": [],
        "timeout": []
    }
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n{'='*80}")
        print(f"Processing file {i}/{len(pdf_files)}: {pdf_path.name}")
        print(f"{'='*80}")
        
        try:
            # Skip known problematic PDFs temporarily
            if "3M India Ltd" in pdf_path.name and ("2019_20" in pdf_path.name or "2020_21" in pdf_path.name):
                print(f"  Skipping known problematic file: {pdf_path.name}")
                results["skipped"].append({
                    "pdf_path": str(pdf_path),
                    "status": "skipped",
                    "reason": "known_problematic_file"
                })
                continue
            
            result = process_single_pdf(pdf_path)
            status = result.get("status", "failed")
            
            if status == "success":
                results["success"].append(result)
            elif status == "skipped":
                results["skipped"].append(result)
            elif "timeout" in result.get("error", ""):
                results["timeout"].append(result)
            else:
                results["failed"].append(result)
        
        except KeyboardInterrupt:
            # Catch KeyboardInterrupt from problematic PDFs in pdfplumber
            print(f"  ⚠ PDF caused interrupt (problematic): {pdf_path.name}")
            results["failed"].append({
                "pdf_path": str(pdf_path),
                "status": "failed",
                "error": "keyboard_interrupt_from_pdfplumber"
            })
            continue
                
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            results["failed"].append({
                "pdf_path": str(pdf_path),
                "error": str(e)
            })
    
    # Print summary
    print("\n" + "="*80)
    print("BATCH PROCESSING SUMMARY")
    print("="*80)
    print(f"Total PDFs: {len(pdf_files)}")
    print(f"Successfully processed: {len(results['success'])}")
    print(f"Skipped (already done): {len(results['skipped'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Timeout: {len(results['timeout'])}")
    
    # Save summary to JSON
    summary_file = Path(__file__).parent.parent / "config" / "logs" / "batch_summary_15companies.json"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nSummary saved to: {summary_file}")
    
    # List timeout/failed companies
    if results["timeout"]:
        print("\nTimed out:")
        for r in results["timeout"]:
            print(f"  - {r.get('company', 'Unknown')}: {Path(r['pdf_path']).name}")
    
    if results["failed"]:
        print("\nFailed:")
        for r in results["failed"]:
            print(f"  - {r.get('company', 'Unknown')}: {Path(r['pdf_path']).name}")
            if "error" in r:
                print(f"    Error: {r['error']}")


if __name__ == "__main__":
    main()
