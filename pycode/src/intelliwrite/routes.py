import os
import logging
from flask import Blueprint, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import shutil
import tempfile
from werkzeug.utils import secure_filename

try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
except ImportError:
    sentry_sdk = None
    FlaskIntegration = None

_logger = logging.getLogger(__name__)

from intelliwrite.aeo_blog_engine.services import (
    generate_and_store_blog,
    store_social_post,
    fetch_blog_by_user,
    fetch_blog,
)
from intelliwrite.aeo_blog_engine.knowledge.ingest import ingest_docs
from intelliwrite.aeo_blog_engine.pipeline.blog_workflow import AEOBlogPipeline

load_dotenv()

# sentry_sdk.init(
#     dsn=os.getenv("SENTRY_DSN"),
#     integrations=[FlaskIntegration()],
#     send_default_pii=True,
#     enable_logs=True,
#     traces_sample_rate=1.0,
#     profile_session_sample_rate=1.0,
#     profile_lifecycle="trace",
# )

def _capture_exception(exc):
    """Safely capture exception to Sentry if available."""
    if sentry_sdk is not None:
        sentry_sdk.capture_exception(exc)
    else:
        _logger.error("Exception occurred: %s", exc, exc_info=True)

bp = Blueprint("intelliwrite", __name__)

DEFAULT_CORS_ORIGINS = [
    "https://app.cognerd.in",
    "https://intelliwrite.vercel.app",
    "http://localhost:3000",
]
_env_origins = os.getenv("CORS_ALLOWED_ORIGINS")
if _env_origins:
    allowed_origins = [origin.strip() for origin in _env_origins.split(",") if origin.strip()]
else:
    allowed_origins = DEFAULT_CORS_ORIGINS
_origin_set = set(allowed_origins) if "*" not in allowed_origins else None

# Apply CORS when blueprint is registered
@bp.record_once
def _configure(state):
    app = state.app
    CORS(
        app,
        resources={r"/intelliwrite/*": {"origins": allowed_origins if _origin_set else "*"}},
        methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=False,
    )

@bp.after_app_request
def _apply_cors_headers(response):
    origin = request.headers.get("Origin")
    allow_origin = None
    if _origin_set is None:
        allow_origin = origin or "*"
    elif origin in _origin_set:
        allow_origin = origin

    if allow_origin:
        response.headers["Access-Control-Allow-Origin"] = allow_origin
        response.headers["Vary"] = "Origin"
    response.headers.setdefault(
        "Access-Control-Allow-Headers",
        "Content-Type, Authorization, X-Requested-With",
    )
    response.headers.setdefault(
        "Access-Control-Allow-Methods",
        "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    )
    return response


@bp.route("/", methods=["GET"])
def root():
    return jsonify(
        {
            "status": "AEO Blog Engine API is running",
            "endpoints": [
                "POST /intelliwrite/blogs",
                "GET /intelliwrite/blogs/<id>",
                "GET /intelliwrite/blogs/latest",
                "GET /intelliwrite/blogs/latest/topic",
                "GET /intelliwrite/blogs/latest/social",
                "POST /intelliwrite/ingest",
                "POST /intelliwrite/generate-social",
            ],
        }
    )


@bp.route("/favicon.ico")
def favicon():
    return "", 204


@bp.route("/blogs/latest", methods=["GET"])
def get_latest_blog_full():
    user_id = request.args.get("user_id")
    brand_url = request.args.get("brand_url")

    if not user_id or not brand_url:
        return jsonify({"error": "Missing user_id or brand_url parameters"}), 400

    try:
        blog = fetch_blog_by_user(user_id, brand_url)
        if not blog:
            return jsonify({"error": "Blog not found"}), 404
        return jsonify(blog)
    except Exception as exc:
        _capture_exception(exc)
        return jsonify({"error": "Failed to fetch blog", "details": str(exc)}), 500


@bp.route("/blogs/latest/topic", methods=["GET"])
def get_latest_blog_topic():
    user_id = request.args.get("user_id")
    brand_url = request.args.get("brand_url")

    if not user_id or not brand_url:
        return jsonify({"error": "Missing user_id or brand_url parameters"}), 400

    try:
        blog = fetch_blog_by_user(user_id, brand_url)
        if not blog:
            return jsonify({"error": "Blog not found"}), 404

        topic_doc = blog.get("topic") or {}
        return jsonify({"topic": topic_doc})
    except Exception as exc:
        _capture_exception(exc)
        return jsonify({"error": "Failed to fetch topic", "details": str(exc)}), 500


@bp.route("/blogs/latest/social", methods=["GET"])
def get_latest_blog_social():
    user_id = request.args.get("user_id")
    brand_url = request.args.get("brand_url")

    if not user_id or not brand_url:
        return jsonify({"error": "Missing user_id or brand_url parameters"}), 400

    try:
        blog = fetch_blog_by_user(user_id, brand_url)
        if not blog:
            return jsonify({"error": "Blog not found"}), 404

        return jsonify(
            {
                "twitter_post": blog.get("twitter_post", []),
                "linkedin_post": blog.get("linkedin_post", []),
                "reddit_post": blog.get("reddit_post", []),
            }
        )
    except Exception as exc:
        _capture_exception(exc)
        return jsonify({"error": "Failed to fetch social posts", "details": str(exc)}), 500


@bp.route("/ingest", methods=["POST"])
def ingest_knowledge():
    uploaded_files = []
    temp_dir = None

    try:
        if "files" in request.files:
            files = request.files.getlist("files")
            if files:
                temp_dir = tempfile.mkdtemp()
                for file in files:
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(temp_dir, filename)
                        file.save(file_path)
                        uploaded_files.append(filename)

        ingest_docs(upload_dir=temp_dir)

        response = {
            "status": "success",
            "message": "Knowledge base ingested successfully",
        }

        if uploaded_files:
            response["uploaded_files"] = uploaded_files

        return jsonify(response), 200

    except Exception as exc:
        _capture_exception(exc)
        return jsonify({"error": "Failed to ingest knowledge", "details": str(exc)}), 500

    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@bp.route("/blogs", methods=["POST"])
def create_blog():
    data = request.get_json(force=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body; expected an object."}), 400
    try:
        result = generate_and_store_blog(data)
        return jsonify(result), 201
    except ValueError as exc:
        _capture_exception(exc)
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        _capture_exception(exc)
        return (
            jsonify(
                {
                    "error": "Failed to generate blog",
                    "details": str(exc),
                    "hint": "This usually happens when the upstream Gemini quota is exhausted. Please wait a few seconds and try again or top up your quota.",
                }
            ),
            429,
        )
    except Exception as exc:
        _capture_exception(exc)
        return jsonify({"error": "Failed to generate blog", "details": str(exc)}), 500


@bp.route("/generate-social", methods=["POST"])
def generate_social_post():
    data = request.get_json(force=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body; expected an object."}), 400

    topic = data.get("topic")
    platform = data.get("platform")
    user_id = data.get("user_id")
    brand_url = data.get("brand_url")
    brand_name = data.get("brand_name")
    brand_industry = data.get("brand_industry")
    brand_location = data.get("brand_location")
    timestamp = data.get("timestamp")

    if not topic or not platform or not user_id or not brand_url:
        return jsonify({"error": "'topic', 'platform', 'user_id', and 'brand_url' are required."}), 400

    valid_platforms = ["reddit", "linkedin", "twitter"]
    if platform.lower() not in valid_platforms:
        return jsonify({"error": f"Invalid platform. Choose from: {valid_platforms}"}), 400

    try:
        pipeline = AEOBlogPipeline()
        post_content = pipeline.run_social_post(
            topic,
            platform,
            brand_name=brand_name,
            brand_url=brand_url,
            brand_industry=brand_industry,
            brand_location=brand_location,
        )
        saved = store_social_post(
            user_id,
            brand_url,
            topic,
            platform,
            post_content,
            brand_name=brand_name,
            brand_industry=brand_industry,
            brand_location=brand_location,
            timestamp=timestamp,
        )

        return jsonify(
            {
                "status": "success",
                "topic": topic,
                "platform": platform,
                "content": post_content,
                "blog": saved,
            }
        ), 200

    except RuntimeError as exc:
        _capture_exception(exc)
        return (
            jsonify(
                {
                    "error": "Failed to generate social post",
                    "details": str(exc),
                    "hint": "Likely caused by hitting the Gemini API quota. Please retry after the suggested cooldown or adjust your plan.",
                }
            ),
            429,
        )
    except Exception as exc:
        _capture_exception(exc)
        return jsonify({"error": "Failed to generate social post", "details": str(exc)}), 500


@bp.route("/blogs/<blog_id>", methods=["GET"])
def get_blog(blog_id):
    try:
        blog = fetch_blog(blog_id)
    except ValueError:
        return jsonify({"error": "Blog not found"}), 404

    return jsonify(blog)
