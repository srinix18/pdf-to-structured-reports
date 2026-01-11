"""Quick test to verify letter detection is correct."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.section_boundary_detector import SectionBoundaryDetector

pdf = Path('data/(1) 360 ONE WAM LTD.-20251230T101729Z-1-001/(1) 360 ONE WAM LTD/1_360 ONE WAM LTD._2019_20.pdf')

print("Testing letter detection for 360 ONE WAM 2019...")
print("="*60)

detector = SectionBoundaryDetector(pdf)
detector.extract_layout_metadata()
boundaries = detector.detect_section_boundaries()

letter = boundaries.get('letter_to_stakeholders')

if letter:
    print(f"\nLetter detected: Pages {letter.start_page}-{letter.end_page}")
    print(f"Start heading: {letter.start_heading}")
    print(f"Confidence: {letter.confidence:.2f}")
    
    if letter.start_page == 6 and letter.end_page == 11:
        print("\nSUCCESS! Letter correctly detected as pages 6-11.")
    else:
        print(f"\nWARNING: Expected pages 6-11, got {letter.start_page}-{letter.end_page}")
else:
    print("\nERROR: No letter detected!")
