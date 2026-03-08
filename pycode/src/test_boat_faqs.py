"""
Generate FAQs for BOAT (boat-lifestyle.com)
Run from PyCode/: python src/test_boat_faqs.py
"""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from geo_files.faqs import run_faq_pipeline

print("=" * 60)
print("  GEO FAQ Pipeline — BOAT")
print("  URL: https://www.boat-lifestyle.com/")
print("=" * 60)

result = run_faq_pipeline(
    customer_name="Boat",
    url="https://www.boat-lifestyle.com/",
    industry="Consumer Electronics / Audio",
    target_audience="Young adults, music lovers, fitness enthusiasts aged 18-35",
    competitors=["Sony", "JBL", "Noise", "OnePlus", "boAt"],
    max_pages=5,
)

print()
if result["success"]:
    print(f"[DONE] FAQ Generation Successful!")
    print(f"  FAQs generated : {result['faq_count']}")
    print(f"  Pages crawled  : {result['pages_crawled']}")
    print(f"  Output .md     : {result['md_path']}")
    print(f"  Output dir     : {result['output_dir']}")
else:
    print(f"[FAIL] Pipeline failed: {result['error']}")

sys.exit(0 if result["success"] else 1)
