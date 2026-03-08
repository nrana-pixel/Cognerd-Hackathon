from pathlib import Path
import sys

from flask import Flask, jsonify
from flask_cors import CORS

CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from intelliwrite.routes import bp as intelliwrite_bp
from aeo_reports.routes import aeo_reports_bp
from geo_files.routes import geo_files_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(intelliwrite_bp, url_prefix="/intelliwrite")
    app.register_blueprint(aeo_reports_bp, url_prefix="/aeo-reports")
    app.register_blueprint(geo_files_bp, url_prefix="/geo-files")

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
