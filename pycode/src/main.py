"""
MAIN ENTRY POINT FOR PYCODE
Centralized script to run various database operations and utilities.

Created by: Aman Mundra
Date: 2026-02-04

Edited by: Ayushi, Aman 
"""

########################################################################
# ToDo
# - [ ] Maintain a single main.py that can run all database operations and utilities
# - [ ] Add error handling and logging for each module and configure via utils.py
# - [ ] Ensure all database operations are modular and can be run independently or together
# - [ ] Maintain a single requirements.txt that includes all dependencies for the entire project
# - [ ] Add documentation and comments to each module for clarity
# - [ ] Implement .env configuration for database credentials and other sensitive information properly
# - [ ] Remove migrate files/code and force_migration file after confirming with Krishna )
########################################################################

import sys
import io
from pathlib import Path
import argparse
from intelliwrite.aeo_blog_engine.knowledge.ingest import ingest_docs
from intelliwrite.aeo_blog_engine.pipeline.blog_workflow import AEOBlogPipeline
from intelliwrite.aeo_blog_engine.services import generate_and_store_blog, store_social_post 
from utils.utils import check_openrouter_quota

# Ensure the src directory (where the config package lives) is on sys.path
CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parent  # .../PyCode/src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database.mongoDB import main as mongo_main
from database.qdrantDB import main as qdrant_main
from database.neonDB import main as neon_main

# Force UTF-8 stdout/stderr to avoid Windows console encoding issues
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def run_blog_engine(args):
    if args.ingest:
        ingest_docs()

    # Determine topic: use provided arg, or generate from prompt
    topic = args.topic

    # Initialize pipeline once if we have work to do
    pipeline = None
    if args.topic or args.prompt:
        pipeline = AEOBlogPipeline()

        if args.prompt and not topic:
            print(f"Generating topic from prompt: '{args.prompt}'...")
            topic = pipeline.generate_topic_only(args.prompt)
            print(f"-> Generated Topic: {topic}")

    if topic:
        if args.platform:
            # Generate social media post
            post = pipeline.run_social_post(
                topic,
                args.platform,
                brand_name=args.brand,
                brand_url=args.brand_url,
                brand_industry=None,
                brand_location=None,
            )
            print(f"\n--- {args.platform.upper()} POST ---\n")
            print(post)

            # Save to database
            if not args.user_id or not args.brand_url:
                print("\n[WARN] Cannot store social post without --user-id and --brand-url")
            else:
                try:
                    saved = store_social_post(
                        args.user_id,
                        args.brand_url,
                        topic,
                        args.platform,
                        post,
                        brand_name=args.brand,
                    )
                    print(f"\n[DB] Saved {args.platform} post to Blog ID: {saved['id']}")
                except Exception as e:
                    print(f"\n[DB Error] Could not save post: {e}")

        elif args.brand_url and args.user_id:
            # Generate blog and store it
            payload = {
                "topic": topic,
                "prompt": args.prompt,  # Pass prompt for context/logging if needed
                "brand_url": args.brand_url,
                "user_id": args.user_id,
                "email_id": args.email,
                "brand_name": args.brand,
            }
            result = generate_and_store_blog(payload)
            print(result)

        else:
            # Generate blog only
            result = pipeline.run(
                topic,
                brand_name=args.brand,
                brand_url=args.brand_url,
            )
            print("\n--- BLOG CONTENT ---\n")
            print(result)

    else:
        if not args.ingest:
            print("No valid arguments provided.")

    # Ensure Langfuse traces are sent if Langfuse is available
    # if langfuse:
        # langfuse.flush()

# Extend the main function to include blog engine functionality
def main():
    """Main function to run database operations and blog engine."""
    parser = argparse.ArgumentParser(description="PyCode Main CLI")

    # Database operations
    parser.add_argument(
        "--run-database",
        action="store_true",
        help="Run database operations (MongoDB, Qdrant, Neon)"
    )

    # Blog engine arguments
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Ingest documents into Knowledge Base before running"
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Topic to generate a blog for"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Raw prompt to convert into a blog topic (e.g. 'write about fast shoes')"
    )
    parser.add_argument(
        "--brand-url",
        dest="brand_url",
        type=str,
        help="Brand URL associated with the generated content"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="User ID associated with the generated content"
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Contact email to store with the generated blog"
    )
    parser.add_argument(
        "--brand",
        type=str,
        help="Brand name to store with the generated blog"
    )
    parser.add_argument(
        "--platform",
        type=str,
        choices=["reddit", "linkedin", "twitter"],
        help="Generate a social media post for a specific platform"
    )
    parser.add_argument(
        "--check-quota",
        action="store_true",
        help="Check OpenRouter API quota and limits"
    )

    # AEO Report arguments
    parser.add_argument(
        "--aeo-report",
        action="store_true",
        help="Generate an AEO audit report for a website"
    )
    parser.add_argument(
        "--customer-name",
        type=str,
        help="Customer/brand name for the AEO report"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Website URL to audit for the AEO report"
    )
    parser.add_argument(
        "--domain-regex",
        type=str,
        default=None,
        help="Regex to identify internal links for AEO report (optional)"
    )

    # GEO-Faqs arguments
    parser.add_argument(
        "--geo-faqs",
        action="store_true",
        help="Generate a FAQ .md file for a website using crawl4ai + AI agents"
    )
    parser.add_argument(
        "--industry",
        type=str,
        default="",
        help="Industry/sector of the brand (optional, for geo-faqs)"
    )
    parser.add_argument(
        "--target-audience",
        type=str,
        default="",
        help="Target audience description (optional, for geo-faqs)"
    )
    parser.add_argument(
        "--competitors",
        type=str,
        nargs="+",
        default=[],
        help="List of competitor names (optional, for geo-faqs)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=15,
        help="Max pages to crawl from sitemap (default: 15, for geo-faqs)"
    )

    args = parser.parse_args()

    if args.check_quota:
        import json
        from config.settings import Config
        print("\nChecking OpenRouter Quota...")
        quota = check_openrouter_quota(Config.OPENROUTER_API_KEY)
        print(json.dumps(quota, indent=2))

    # --- AEO Report ---
    if args.aeo_report:
        if not args.customer_name or not args.url:
            parser.error("--aeo-report requires --customer-name and --url")
        print("\n" + "="*60)
        print(f"AEO Report Generation: {args.customer_name} — {args.url}")
        print("="*60 + "\n")

        from aeo_reports.report import run_aeo_pipeline
        result = run_aeo_pipeline(
            customer_name=args.customer_name,
            url=args.url,
            domain_regex=args.domain_regex,
        )
        if result["success"]:
            print(f"\n✅ Report generated successfully!")
            print(f"   Path: {result['report_path']}")
        else:
            print(f"\n❌ Report generation failed: {result['error']}")

    # --- GEO FAQs ---
    if args.geo_faqs:
        if not args.customer_name or not args.url:
            parser.error("--geo-faqs requires --customer-name and --url")
        print("\n" + "="*60)
        print(f"GEO FAQ Generation: {args.customer_name} — {args.url}")
        print("="*60 + "\n")

        from geo_files.faqs import run_faq_pipeline
        result = run_faq_pipeline(
            customer_name=args.customer_name,
            url=args.url,
            industry=args.industry,
            target_audience=args.target_audience,
            competitors=args.competitors,
            max_pages=args.max_pages,
        )
        if result["success"]:
            print(f"\n✅ FAQ file generated successfully!")
            print(f"   FAQs: {result['faq_count']}")
            print(f"   Pages crawled: {result['pages_crawled']}")
            print(f"   Path: {result['md_path']}")
        else:
            print(f"\n❌ FAQ generation failed: {result['error']}")


        print("\n" + "="*60)
        print("PyCode Database Operations")
        print("="*60 + "\n")

        results = {}

        # Run MongoDB inspection
        print("Running MongoDB inspection...")
        mongo_success = mongo_main()
        results['MongoDB'] = mongo_success

        print("\n" + "-"*60 + "\n")

        # Run Qdrant inspection
        print("Running Qdrant inspection...")
        qdrant_success = qdrant_main()
        results['Qdrant'] = qdrant_success

        print("\n" + "-"*60 + "\n")

        # Run Neon inspection
        print("Running Neon inspection...")
        neon_success = neon_main()
        results['Neon'] = neon_success

        # Summary
        print("\n" + "="*60)
        print("Operations Summary:")
        print("="*60)
        for db_name, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            print(f"  {db_name}: {status}")

        all_success = all(results.values())
        if all_success:
            print("\n✅ All operations completed successfully")
        else:
            print("\n⚠️ Some operations failed - check logs for details")

    # Run blog engine if any blog-related arguments are provided
    if args.ingest or args.topic or args.prompt or args.platform:
        run_blog_engine(args)

if __name__ == "__main__":
    main()
