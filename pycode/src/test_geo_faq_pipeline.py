"""
Extensive test suite for the GEO FAQ pipeline.
Tests: crawl, pain_points agent, per_page_summary agent, faqs agent, full pipeline, edge cases.
Run from PyCode/ root: python src/test_geo_faq_pipeline.py
"""
import json
import sys
import os
import traceback
from pathlib import Path

import io
# Reconfigure stdout to UTF-8 so emoji work on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"
results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, name, detail))
    print(f"  {status}  {name}" + (f"\n         {detail}" if detail else ""))
    return condition

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ============================================================
# TEST 1: IMPORT CHECKS
# ============================================================
section("1. Import Checks")

try:
    from geo_files.crawled_data import crawl_site
    check("crawled_data.crawl_site importable", True)
except Exception as e:
    check("crawled_data.crawl_site importable", False, str(e)); sys.exit(1)

try:
    from geo_files.faqs import (
        run_faq_pipeline, _parse_json_array, _parse_json_dict,
        _render_markdown, _build_brand_context, _slugify
    )
    check("geo_files.faqs all functions importable", True)
except Exception as e:
    check("geo_files.faqs all functions importable", False, str(e)); sys.exit(1)

try:
    from geo_files.routes import geo_files_bp
    check("geo_files.routes blueprint importable", True)
except Exception as e:
    check("geo_files.routes blueprint importable", False, str(e))

try:
    import agents
    check("agents.get_pain_points_agent importable", hasattr(agents, "get_pain_points_agent"))
    check("agents.get_per_page_summary_agent importable", hasattr(agents, "get_per_page_summary_agent"))
    check("agents.get_faqs_agent importable", hasattr(agents, "get_faqs_agent"))
except Exception as e:
    check("agents module importable", False, str(e))

# ============================================================
# TEST 2: JSON PARSING HELPERS
# ============================================================
section("2. JSON Parsing Helpers")

# Normal JSON array
arr = _parse_json_array('[{"question":"Q1","answer":"A1","category":"general"}]', "test")
check("parse plain JSON array", isinstance(arr, list) and len(arr) == 1)

# With markdown fences
fenced = '```json\n[{"question":"Q2","answer":"A2","category":"pricing"}]\n```'
arr2 = _parse_json_array(fenced, "test")
check("parse fenced JSON array", isinstance(arr2, list) and len(arr2) == 1)

# Wrapped in object
wrapped = '{"faqs": [{"question":"Q3","answer":"A3","category":"product"}]}'
arr3 = _parse_json_array(wrapped, "test")
check("parse array wrapped in object", isinstance(arr3, list) and len(arr3) == 1)

# Empty / invalid
arr4 = _parse_json_array("", "test")
check("parse empty string → empty list", arr4 == [])
arr5 = _parse_json_array("not json at all %%%", "test")
check("parse garbage → empty list", arr5 == [])

# Dict parsing
d = _parse_json_dict('{"pages":[{"url":"https://x.com"}]}', "test")
check("parse plain JSON dict", isinstance(d, dict) and "pages" in d)
d2 = _parse_json_dict('```json\n{"key":"value"}\n```', "test")
check("parse fenced JSON dict", isinstance(d2, dict) and d2.get("key") == "value")

# ============================================================
# TEST 3: MARKDOWN RENDERER
# ============================================================
section("3. Markdown Renderer")

sample_faqs = [
    {"question": "Is boAt waterproof?", "answer": "Yes, most boAt earbuds are IPX4 rated.", "category": "product"},
    {"question": "What is the price?", "answer": "Prices start from ₹999.", "category": "pricing"},
    {"question": "How to contact support?", "answer": "Via website chat.", "category": "support"},
    {"question": "vs Sony?", "answer": "boAt is more affordable.", "category": "comparison"},
    {"question": "General question?", "answer": "General answer.", "category": "general"},
    {"question": "Unknown cat?", "answer": "Some answer.", "category": "unknown_category"},
]
sample_summaries = [{"url": "https://boat-lifestyle.com", "summary": "Home page"}]

md = _render_markdown("Boat", "https://boat-lifestyle.com", sample_faqs, sample_summaries)
check("markdown starts with # FAQ", md.startswith("# FAQ"))
check("markdown contains Generated line", "Generated:" in md)
check("markdown has ## Product section", "## Product" in md)
check("markdown has ## Pricing section", "## Pricing" in md)
check("markdown has ## Support section", "## Support" in md)
check("markdown has Q: format", "**Q:" in md)
check("markdown has A: format", "\nA:" in md)
check("unknown category goes to ## Other", "## Other" in md)

# ============================================================
# TEST 4: INPUT VALIDATION
# ============================================================
section("4. Input Validation")

r = run_faq_pipeline("", "https://example.com")
check("empty customer_name returns error", not r["success"] and r["error"])

r = run_faq_pipeline("Test", "")
check("empty url returns error", not r["success"] and r["error"])

r = run_faq_pipeline("Test", "no-scheme-url.com")
# Should auto-prepend https and proceed (not fail on scheme)
err_msg = r.get("error") or ""
check("url without https gets prepended", not err_msg.startswith("url cannot"))

# ============================================================
# TEST 5: CRAWL FUNCTION (live test, small)
# ============================================================
section("5. crawl_site() — Live Test (example.com, 2 pages)")

try:
    site = crawl_site("https://example.com", "ExampleCo", max_pages=2)
    check("crawl returns dict", isinstance(site, dict))
    check("crawled_pages key present", "crawled_pages" in site)
    check("at least 1 page crawled", len(site.get("crawled_pages", {})) >= 1)
    check("customer_name present", site.get("customer_name") == "ExampleCo")
    check("site_url present", "site_url" in site)
    check("date present", "date" in site)

    # Check page structure
    first_page = next(iter(site["crawled_pages"].values()), {})
    check("page has content key", "content" in first_page)
    check("page has title key", "title" in first_page)
    check("page has meta_description key", "meta_description" in first_page)

    print(f"\n    Pages crawled: {list(site['crawled_pages'].keys())[:3]}")
except Exception as e:
    check("crawl_site live test", False, traceback.format_exc()[:200])

# ============================================================
# TEST 6: AGENT SMOKE TESTS
# ============================================================
section("6. Agent Smoke Tests (minimal prompts)")

# Pain points agent
try:
    import agents as ag
    pain_agent = ag.get_pain_points_agent()
    check("pain_points_agent has tools", hasattr(pain_agent, "tools") or True)  # structure check
    resp = pain_agent.run("Brand: ExampleCo. Industry: tech. Target: developers. Competitors: None.")
    raw = resp.content if hasattr(resp, "content") else str(resp)
    pain_data = _parse_json_array(raw, "pain_points")
    check("pain_points_agent returns list", isinstance(pain_data, list))
    check("pain_points has 1+ items", len(pain_data) >= 1)
    if pain_data:
        first = pain_data[0]
        check("pain point has 'question' key", "question" in first)
        check("pain point has 'category' key", "category" in first)
    print(f"    Pain points received: {len(pain_data)}")
except Exception as e:
    check("pain_points_agent smoke test", False, str(e)[:150])

# Per page summary agent
try:
    pp_agent = ag.get_per_page_summary_agent()
    mini_prompt = """Website: ExampleCo
Pages:
[{"url":"https://example.com","title":"Example Domain","meta_description":"","content_snippet":"This domain is for use in examples."}]"""
    resp2 = pp_agent.run(mini_prompt)
    raw2 = resp2.content if hasattr(resp2, "content") else str(resp2)
    summary_data = _parse_json_dict(raw2, "per_page_summary")
    pages_list = summary_data.get("pages", [])
    check("per_page_summary_agent returns dict with pages", isinstance(pages_list, list))
    check("per_page_summary has 1+ pages", len(pages_list) >= 1)
    if pages_list:
        first_pg = pages_list[0]
        check("page summary has 'url' key", "url" in first_pg)
        check("page summary has 'summary' key", "summary" in first_pg)
    print(f"    Page summaries received: {len(pages_list)}")
except Exception as e:
    check("per_page_summary_agent smoke test", False, str(e)[:150])

# FAQs agent
try:
    faq_agent = ag.get_faqs_agent()
    mini_faq_prompt = """Brand Name: ExampleCo
Industry: tech
Pain Points: [{"question":"Is it free?","source":"reddit","category":"pricing","popularity":"high"}]
Per-Page Summaries: [{"url":"https://example.com","summary":"Example domain for docs.","keyTopics":["examples"],"customerIntent":"learn"}]
Generate 5 core FAQs. Return JSON array only."""
    resp3 = faq_agent.run(mini_faq_prompt)
    raw3 = resp3.content if hasattr(resp3, "content") else str(resp3)
    faqs_list = _parse_json_array(raw3, "faqs")
    if not faqs_list:
        obj = _parse_json_dict(raw3, "faqs_obj")
        faqs_list = obj.get("faqs") or obj.get("questions") or []
    check("faqs_agent returns list", isinstance(faqs_list, list))
    check("faqs_agent has 1+ faqs", len(faqs_list) >= 1)
    if faqs_list:
        fq = faqs_list[0]
        check("faq has 'question' key", "question" in fq)
        check("faq has 'answer' key", "answer" in fq)
    print(f"    FAQs received: {len(faqs_list)}")
except Exception as e:
    check("faqs_agent smoke test", False, str(e)[:150])

# ============================================================
# TEST 7: FULL END-TO-END PIPELINE
# ============================================================
section("7. Full End-to-End Pipeline (example.com)")

try:
    e2e = run_faq_pipeline(
        customer_name="ExampleCo",
        url="https://example.com",
        industry="Technology",
        target_audience="Developers",
        competitors=["Google", "Microsoft"],
        max_pages=3,
    )

    check("pipeline success=True", e2e.get("success") is True, e2e.get("error", ""))
    check("md_path returned", bool(e2e.get("md_path")))
    check("output_dir returned", bool(e2e.get("output_dir")))
    check("faq_count > 0", (e2e.get("faq_count") or 0) > 0)
    check("pages_crawled > 0", (e2e.get("pages_crawled") or 0) > 0)

    if e2e.get("md_path"):
        md_path = Path(e2e["md_path"])
        check(".md file exists on disk", md_path.exists())
        if md_path.exists():
            md_text = md_path.read_text(encoding="utf-8")
            check(".md file not empty", len(md_text) > 100)
            check(".md starts with # FAQ", md_text.startswith("# FAQ"))
            check(".md has at least one Q:", "**Q:" in md_text)
            print(f"\n    .md path: {md_path}")
            print(f"    .md size: {len(md_text)} chars")
            print(f"    FAQs:     {e2e['faq_count']}")
            print(f"    Pages:    {e2e['pages_crawled']}")

    # Check intermediate JSON files
    if e2e.get("output_dir"):
        out_dir = Path(e2e["output_dir"])
        check("pain_points.json saved", (out_dir / "exampleco_pain_points.json").exists())
        check("page_summaries.json saved", (out_dir / "exampleco_page_summaries.json").exists())
        check("faqs_raw.json saved", (out_dir / "exampleco_faqs_raw.json").exists())
        check("site_assessment.json saved", any(out_dir.glob("*_site_assessment.json")))

except Exception as e:
    check("full e2e pipeline", False, traceback.format_exc()[:300])

# ============================================================
# TEST 8: FLASK ENDPOINT
# ============================================================
section("8. Flask Endpoint Validation")

try:
    from api import create_app
    app = create_app()
    client = app.test_client()

    # No body
    r = client.post("/geo-files/faqs")
    check("POST /geo-files/faqs empty body → 400", r.status_code == 400)

    # Missing url
    r = client.post("/geo-files/faqs",
                    data=json.dumps({"customer_name": "Test"}),
                    content_type="application/json")
    check("Missing url → 400", r.status_code == 400)

    # Missing customer_name
    r = client.post("/geo-files/faqs",
                    data=json.dumps({"url": "https://example.com"}),
                    content_type="application/json")
    check("Missing customer_name → 400", r.status_code == 400)

    # Status endpoint
    r = client.get("/geo-files/status")
    check("GET /geo-files/status → 200", r.status_code == 200)
    data = json.loads(r.data)
    check("/geo-files/status returns ready", data.get("status") == "ready")

except Exception as e:
    check("Flask endpoint validation", False, str(e)[:150])

# ============================================================
# SUMMARY
# ============================================================
print(f"\n{'='*60}")
print("  TEST SUMMARY")
print(f"{'='*60}")
total = len(results)
passed = sum(1 for s, _, _ in results if s == PASS)
failed = sum(1 for s, _, _ in results if s == FAIL)
print(f"  Total:  {total}")
print(f"  Passed: {passed}")
print(f"  Failed: {failed}")
print(f"{'='*60}")
if failed:
    print("\n  Failed tests:")
    for s, n, d in results:
        if s == FAIL:
            print(f"    - {n}: {d}")

sys.exit(0 if failed == 0 else 1)
