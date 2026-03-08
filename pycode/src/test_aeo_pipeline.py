"""
Run AEO pipeline for boat-lifestyle.com
"""
import json
import sys

print("=" * 60)
print("Generating AEO Report: Boat Lifestyle")
print("URL: https://www.boat-lifestyle.com")
print("=" * 60)

from aeo_reports.report import run_aeo_pipeline

result = run_aeo_pipeline(
    customer_name="Boat",
    url="https://www.boat-lifestyle.com",
)

print("\n" + "=" * 60)
print("RESULT:")
summary = {k: v for k, v in result.items() if k != "html"}
print(json.dumps(summary, indent=2, default=str))

if result.get("html"):
    print(f"\nHTML size: {len(result['html'])} chars")

if result["success"]:
    print(f"\n✅ Report saved at:")
    print(f"   {result['report_path']}")
else:
    print(f"\n❌ Failed: {result['error']}")
    sys.exit(1)
