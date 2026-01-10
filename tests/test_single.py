"""Quick test script to process one PDF"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import process_single_pdf

pdf_path = Path(r'data/(17) Adani Green Energy Ltd.-20251230T103344Z-1-001/(17) Adani Green Energy Ltd/17_Adani Green Energy Ltd._2019_20.pdf')

print("Processing:", pdf_path.name)
print("="*80)

result = process_single_pdf(pdf_path)

print("\n" + "="*80)
print("STATUS:", result['status'])
if result['status'] == 'success':
    print("Files created:", len(result.get('files_created', [])))
    print("CSV files:", len(result.get('csv_files', [])))
print("="*80)
