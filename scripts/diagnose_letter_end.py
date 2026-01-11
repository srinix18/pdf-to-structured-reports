"""Diagnose what marks the end of the letter around page 11-12."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.section_boundary_detector import SectionBoundaryDetector

pdf = Path('data/(1) 360 ONE WAM LTD.-20251230T101729Z-1-001/(1) 360 ONE WAM LTD/1_360 ONE WAM LTD._2019_20.pdf')

print("Extracting layout metadata...")
detector = SectionBoundaryDetector(pdf)
detector.extract_layout_metadata()

print("\n" + "="*80)
print("BLOCKS FROM PAGES 10-15 (checking for letter end marker)")
print("="*80)

for page in range(10, 16):
    print(f"\n--- PAGE {page} ---")
    page_blocks = [b for b in detector.text_blocks if b.page_number == page]
    
    # Calculate median font for this page
    page_fonts = [b.font_size for b in page_blocks if b.font_size > 0]
    median_font = sorted(page_fonts)[len(page_fonts) // 2] if page_fonts else 10
    
    for block in page_blocks:
        # Check if it's a potential heading
        is_heading = detector._is_potential_heading(block, None)
        
        if is_heading:
            print(f"\n✓ HEADING DETECTED:")
            print(f"  Text: {block.text[:80]}")
            print(f"  Normalized: {block.normalized_text[:80]}")
            print(f"  Font size: {block.font_size:.1f}pt (median: {median_font:.1f})")
            print(f"  Y-position: {block.y_position:.1f}")
            print(f"  Line length: {len(block.text)}")
        elif block.font_size >= median_font * 1.05 or len(block.text) < 60:
            # Show notable blocks even if not classified as headings
            print(f"\n  Notable block:")
            print(f"    Text: {block.text[:80]}")
            print(f"    Normalized: {block.normalized_text[:80]}")
            print(f"    Font: {block.font_size:.1f}pt")

print("\n" + "="*80)
print("CHECKING CURRENT DETECTION")
print("="*80)

boundaries = detector.detect_section_boundaries()
letter = boundaries.get('letter_to_stakeholders')

if letter:
    print(f"\nCurrent detection: Pages {letter.start_page}-{letter.end_page}")
    print(f"Start heading: {letter.start_heading}")
    print(f"Confidence: {letter.confidence:.2f}")
else:
    print("\nNo letter detected")
