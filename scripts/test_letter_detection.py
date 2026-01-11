"""Quick test of letter detection on reports that previously failed"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.section_boundary_detector import SectionBoundaryDetector

pdfs = [
    'data/(1) 360 ONE WAM LTD.-20251230T101729Z-1-001/(1) 360 ONE WAM LTD/1_360 ONE WAM LTD._2019_20.pdf',
    'data/(1) 360 ONE WAM LTD.-20251230T101729Z-1-001/(1) 360 ONE WAM LTD/1_360 ONE WAM LTD._2020_21.pdf',
    'data/(11) Aarti Industries Ltd.-20251230T102222Z-1-001/(11) Aarti Industries Ltd/11_Aarti Industries Ltd._2019_20.pdf'
]

for pdf_str in pdfs:
    pdf = Path(pdf_str)
    if not pdf.exists():
        continue
    print(f'\n{pdf.name}:')
    detector = SectionBoundaryDetector(pdf)
    detector.extract_layout_metadata()
    boundaries = detector.detect_section_boundaries()
    letter = boundaries.get('letter_to_stakeholders')
    if letter:
        print(f'  ✓ Letter pages {letter.start_page}-{letter.end_page}: "{letter.start_heading}"')
    else:
        print(f'  ✗ No letter detected')
