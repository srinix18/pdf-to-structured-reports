"""Quick check of how many reports need letter extraction."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.reextract_letters import find_reports_without_letters

reports = find_reports_without_letters()

print(f"Reports without letters: {len(reports)}")
print("\nFirst 10:")
for company, year, output_dir, pdf_path in reports[:10]:
    print(f"  {company} - {year}")

if len(reports) > 10:
    print(f"... and {len(reports)-10} more")
