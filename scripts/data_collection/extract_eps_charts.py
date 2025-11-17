"""
Extract Quarterly Bottom-Up EPS chart pages from FactSet PDFs
"""
import pdfplumber
import os
import glob
from datetime import datetime

# Settings
OUTPUT_DIR = "output/estimates"
PDF_DIR = "output/factset_pdfs"
KEYWORDS = [
    "Bottom-Up EPS Estimates: Current & Historical",
    "Bottom-up EPS Estimates: Current & Historical", 
    "Bottom-Up EPS: Current & Historical",
]
LIMIT = None  # Number of PDFs to extract (None = all)

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# PDF file list (newest first)
pdf_files = sorted(glob.glob(f"{PDF_DIR}/*.pdf"), reverse=True)

print(f"🔍 Extracting EPS charts from FactSet PDFs")
print(f"Target: {len(pdf_files)} PDFs {'all' if LIMIT is None else f'{LIMIT} of'}")
print("=" * 80)

extracted = 0

for pdf_path in pdf_files:
    if LIMIT is not None and extracted >= LIMIT:
        break
    
    filename = os.path.basename(pdf_path)
    
    # Extract date (EarningsInsight_20161209_120916.pdf -> 20161209)
    try:
        date_str = filename.split('_')[1]
        report_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
    except:
        continue
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                
                if text and any(kw in text for kw in KEYWORDS):
                    # Check keyword location (if at bottom of page)
                    keyword_at_bottom = False
                    for word in page.extract_words():
                        if any(kw.split()[0] in word['text'] for kw in KEYWORDS):
                            # If y coordinate is 700 or more, consider it bottom of page
                            if word['top'] > 700:
                                keyword_at_bottom = True
                                break
                    
                    # If keyword is at bottom, extract next page
                    if keyword_at_bottom and page_num + 1 < len(pdf.pages):
                        target_page = pdf.pages[page_num + 1]
                        target_page_num = page_num + 2
                        print(f"   ⚠️  Keyword detected at bottom -> move to next page")
                    else:
                        target_page = page
                        target_page_num = page_num + 1
                    
                    # Save high-resolution image
                    output_path = f"{OUTPUT_DIR}/{date_str}.png"
                    target_page.to_image(resolution=300).save(output_path)
                    
                    print(f"✅ {report_date:12s} Page {target_page_num:2d} -> {output_path}")
                    extracted += 1
                    
                    # Progress (every 10 files)
                    if extracted % 10 == 0:
                        print(f"   📊 Progress: {extracted} files extracted")
                    
                    break
    
    except Exception as e:
        print(f"❌ {report_date:12s} Error: {str(e)[:50]}")

print("\n" + "=" * 80)
print(f"📊 Result: {extracted} files extracted")
