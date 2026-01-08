"""
Compare text extraction between PDF and generated DOCX to validate completeness.
"""
import pdfplumber
from docx import Document
from pathlib import Path

# Paths
pdf_path = Path(r"data\(17) Adani Green Energy Ltd.-20251230T103344Z-1-001\(17) Adani Green Energy Ltd\17_Adani Green Energy Ltd._2019_20.pdf")
docx_path = Path(r"outputs\(17) Adani Green Energy Ltd\2019\report.docx")

print("="*80)
print("PDF vs DOCX Text Comparison")
print("="*80)

# Extract text from PDF (raw copyable text)
print("\n1. Extracting text from PDF...")
pdf_text = []
pdf_char_count = 0

with pdfplumber.open(pdf_path) as pdf:
    total_pages = len(pdf.pages)
    print(f"   Total PDF pages: {total_pages}")
    
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        pdf_text.append(text)
        pdf_char_count += len(text)
        
        if i < 3:  # Show sample from first 3 pages
            print(f"   Page {i+1}: {len(text):,} chars")

print(f"\n   TOTAL PDF characters: {pdf_char_count:,}")

# Extract text from DOCX
print("\n2. Extracting text from DOCX...")
doc = Document(docx_path)
docx_text = []
docx_char_count = 0

for para in doc.paragraphs:
    text = para.text
    docx_text.append(text)
    docx_char_count += len(text)

print(f"   Total DOCX paragraphs: {len(docx_text):,}")
print(f"   TOTAL DOCX characters: {docx_char_count:,}")

# Compare
print("\n" + "="*80)
print("COMPARISON RESULTS")
print("="*80)

diff = pdf_char_count - docx_char_count
diff_pct = (diff / pdf_char_count * 100) if pdf_char_count > 0 else 0

print(f"PDF characters:    {pdf_char_count:>12,}")
print(f"DOCX characters:   {docx_char_count:>12,}")
print(f"Difference:        {diff:>12,} ({diff_pct:+.2f}%)")

if abs(diff_pct) < 5:
    print(f"\n✓ Extraction is EXCELLENT - difference is within 5%")
elif abs(diff_pct) < 10:
    print(f"\n⚠ Extraction is GOOD - difference is within 10%")
else:
    print(f"\n✗ Extraction may have ISSUES - difference is > 10%")

# Character type analysis
print("\n" + "="*80)
print("CHARACTER TYPE ANALYSIS")
print("="*80)

def analyze_text(text):
    full_text = '\n'.join(text)
    return {
        'total': len(full_text),
        'letters': sum(1 for c in full_text if c.isalpha()),
        'digits': sum(1 for c in full_text if c.isdigit()),
        'spaces': sum(1 for c in full_text if c.isspace()),
        'punctuation': sum(1 for c in full_text if not c.isalnum() and not c.isspace()),
    }

pdf_analysis = analyze_text(pdf_text)
docx_analysis = analyze_text(docx_text)

print(f"\n{'Type':<15} {'PDF':>15} {'DOCX':>15} {'Diff':>12}")
print("-" * 60)
for key in ['total', 'letters', 'digits', 'spaces', 'punctuation']:
    pdf_val = pdf_analysis[key]
    docx_val = docx_analysis[key]
    diff = pdf_val - docx_val
    print(f"{key.capitalize():<15} {pdf_val:>15,} {docx_val:>15,} {diff:>12,}")

print("\n" + "="*80)
