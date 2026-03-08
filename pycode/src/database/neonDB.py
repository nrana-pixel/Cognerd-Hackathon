"""
NEON DATABASE CONNECTION, MODELS AND REPOSITORY
This script connects to a Neon PostgreSQL database and retrieves comprehensive
information about all tables, including their structure, relationships, and data.

It also contains the SQLAlchemy models and repository logic.

Created by: Aman Mundra
Date: 2026-02-04
"""

import json
import ssl
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Column, Integer, String, Text, TIMESTAMP, func, 
    create_engine, inspect, text
)
from sqlalchemy.orm import declarative_base, validates, sessionmaker
from sqlalchemy.types import TypeDecorator

from config.settings import Config
from utils.log_utils import get_logger
from utils.mailer import send_db_report_email

from utils.utils import get_current_utc_iso

# Initialize logger
logger = get_logger("neon_inspector")

# --- SQLALCHEMY MODELS START ---

Base = declarative_base()


def _ensure_entry(item):
    if isinstance(item, dict):
        content = item.get("content")
        timestamp = item.get("timestamp")
        is_prompt = item.get("is_prompt")
        topic = item.get("topic")
    else:
        content = item
        timestamp = None
        is_prompt = None
        topic = None

    if content is None:
        return None

    entry = {"content": content, "timestamp": timestamp}
    if is_prompt is not None:
        entry["is_prompt"] = is_prompt
    if topic is not None:
        entry["topic"] = topic
    return entry


def _ensure_entries(items):
    normalized = []
    for item in items or []:
        entry = _ensure_entry(item)
        if entry:
            normalized.append(entry)
    return normalized


def _make_entry(content, timestamp=None, is_prompt=None, topic=None):
    if content is None:
        return None
    if not timestamp:
        timestamp = get_current_utc_iso()
    entry = {"content": content, "timestamp": timestamp}
    if is_prompt is not None:
        entry["is_prompt"] = is_prompt
    if topic is not None:
        entry["topic"] = topic
    return entry


class JSONList(TypeDecorator):
    """Stores Python lists as JSON strings in Text columns."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            value = []
        if not isinstance(value, (list, tuple)):
            value = [value]
        value = _ensure_entries(value)
        return json.dumps(list(value))

    def process_result_value(self, value, dialect):
        if not value:
            return []
        try:
            parsed = json.loads(value)
            parsed = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            parsed = [value]
        return _ensure_entries(parsed)


class Blog(Base):
    __tablename__ = "blogs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Text, nullable=False)
    brand_url = Column(Text, nullable=False)
    email_id = Column(Text)
    brand_name = Column(Text)
    brand_industry = Column(Text)
    brand_location = Column(Text)
    blogs = Column("blog", JSONList, nullable=False, default=list)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    topic = Column(JSONList, nullable=True, default=list)
    status = Column(String, nullable=False, server_default="PENDING")

    # Social Media Content
    twitter_post = Column("twitter_post", JSONList, nullable=True, default=list)
    linkedin_post = Column("linkedin_post", JSONList, nullable=True, default=list)
    reddit_post = Column("reddit_post", JSONList, nullable=True, default=list)

    @staticmethod
    def make_entry(content, timestamp=None, is_prompt=None, topic=None):
        return _make_entry(content, timestamp, is_prompt, topic)

    @staticmethod
    def ensure_entries(items):
        return _ensure_entries(items)

    @staticmethod
    def entry_contents(items):
        contents = []
        for entry in items or []:
            if not isinstance(entry, dict):
                entry = _ensure_entry(entry)
                if entry is None:
                    continue
            contents.append(entry["content"])
        return contents

    @validates("blogs", "topic", "twitter_post", "linkedin_post", "reddit_post")
    def _validate_entries(self, key, value):
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return _ensure_entries(value)
        entry = _ensure_entry(value)
        if entry:
            return [entry]
        return []

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "brand_url": self.brand_url,
            "email_id": self.email_id,
            "brand_name": self.brand_name,
            "brand_industry": self.brand_industry,
            "brand_location": self.brand_location,
            "blogs": self.ensure_entries(self.blogs),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "topic": self.ensure_entries(self.topic),
            "status": self.status,
            "twitter_post": self.ensure_entries(self.twitter_post),
            "linkedin_post": self.ensure_entries(self.linkedin_post),
            "reddit_post": self.ensure_entries(self.reddit_post),
        }

# --- SQLALCHEMY MODELS END ---

# --- DB CONNECTION & SESSION START ---

if not Config.DATABASE_URL:
    logger.warning("DATABASE_URL must be set in environment variables for NeonDB functionality.")
    engine = None
    SessionLocal = None
else:
    # Configure connection args
    connect_args = {}

    # If using pg8000 (which we use for Vercel size limits), we need to handle SSL context explicitly
    # because it doesn't support 'sslmode=require' in the URL query string the same way psycopg2 does.
    if "pg8000" in Config.DATABASE_URL:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False # Optional: depends on Neon's certs, usually safer to disable specific hostname check if using pooler
        ssl_context.verify_mode = ssl.CERT_NONE # For many serverless DBs, verify_mode=NONE is required unless CA bundle is provided
        connect_args["ssl_context"] = ssl_context

    try:
        engine = create_engine(
            Config.DATABASE_URL, 
            pool_pre_ping=True,
            connect_args=connect_args
        )
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    except ModuleNotFoundError as e:
        logger.error(f"❌ Failed to initialize Neon database engine: {e}")
        engine = None
        SessionLocal = None


@contextmanager
def get_session():
    if SessionLocal is None:
        raise RuntimeError("Database engine is not initialized.")
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# --- DB CONNECTION & SESSION END ---

# --- REPOSITORY FUNCTIONS START ---

def get_blog_by_user_and_company(session, *, user_id: str, brand_url: str) -> Optional[Blog]:
    return (
        session.query(Blog)
        .filter(Blog.user_id == user_id, Blog.brand_url == brand_url)
        .order_by(Blog.created_at.desc())
        .first()
    )


def create_blog_entry(
    session,
    *,
    user_id: str,
    topic: str,
    brand_url: str,
    email_id: str = None,
    brand_name: str = None,
    blog: Optional[str] = None,
    status: str = "PENDING",
    twitter_post: Optional[str] = None,
    linkedin_post: Optional[str] = None,
    reddit_post: Optional[str] = None,
    is_prompt: str = "false",
    timestamp: str = None,
):
    entry = Blog(
        user_id=user_id,
        topic=[Blog.make_entry(topic, is_prompt=is_prompt, timestamp=timestamp)] if topic else [],
        brand_url=brand_url,
        email_id=email_id,
        brand_name=brand_name,
        blogs=[Blog.make_entry(blog, timestamp=timestamp)] if blog else [],
        status=status,
        twitter_post=[Blog.make_entry(twitter_post)] if twitter_post else [],
        linkedin_post=[Blog.make_entry(linkedin_post)] if linkedin_post else [],
        reddit_post=[Blog.make_entry(reddit_post)] if reddit_post else [],
    )
    session.add(entry)
    session.flush()  # populate autogenerated fields
    return entry


def get_blog_by_id(session, blog_id):
    return session.query(Blog).filter(Blog.id == blog_id).one_or_none()


def update_blog_status(session, blog_id, *, status, blog_content=None, topic: Optional[str] = None, is_prompt: str = "false", timestamp: str = None):
    blog = get_blog_by_id(session, blog_id)
    if not blog:
        raise ValueError(f"Blog with id {blog_id} not found")

    blog.status = status
    if blog_content is not None:
        blogs = Blog.ensure_entries(blog.blogs)
        entry = Blog.make_entry(blog_content, timestamp=timestamp, topic=topic, is_prompt=is_prompt)
        blogs.append(entry)
        blog.blogs = blogs

    if topic:
        topics = Blog.ensure_entries(blog.topic)
        contents = Blog.entry_contents(topics)
        if topic not in contents:
            topics.append(Blog.make_entry(topic, is_prompt=is_prompt, timestamp=timestamp))
            blog.topic = topics

    session.add(blog)
    session.flush()
    return blog


def append_social_post(session, blog: Blog, platform: str, content: str, topic: Optional[str] = None, timestamp: Optional[str] = None):
    platform = platform.lower()
    new_entry = Blog.make_entry(content, timestamp=timestamp, topic=topic)
    
    if platform == "twitter":
        current_list = Blog.ensure_entries(blog.twitter_post)
    elif platform == "linkedin":
        current_list = Blog.ensure_entries(blog.linkedin_post)
    elif platform == "reddit":
        current_list = Blog.ensure_entries(blog.reddit_post)
    else:
        raise ValueError(f"Unsupported platform for saving: {platform}")

    # Remove existing entries with the same topic to avoid duplicates
    if topic:
        normalized = []
        for entry in current_list:
            if not isinstance(entry, dict):
                entry = Blog.make_entry(entry)
            if entry and entry.get("topic") != topic:
                normalized.append(entry)
        current_list = normalized
    
    current_list.append(new_entry)

    if platform == "twitter":
        blog.twitter_post = current_list
    elif platform == "linkedin":
        blog.linkedin_post = current_list
    elif platform == "reddit":
        blog.reddit_post = current_list

    session.add(blog)
    session.flush()
    return blog

# --- REPOSITORY FUNCTIONS END ---

# --- INSPECTOR FUNCTIONS START ---

def get_database_summary(db_name: str, tables_info: Dict[str, Any]) -> Dict[str, Any]:
    """Get comprehensive database statistics and summary."""
    try:
        if engine is None:
            logger.error("❌ Cannot get database summary because the database engine is not initialized.")
            return {}

        with engine.connect() as conn:
            db_size_bytes = conn.execute(text(f"SELECT pg_database_size('{db_name}')")).scalar()

        total_rows = sum(table.get('stats', {}).get('count', 0) for table in tables_info.values())
        total_tables = len(tables_info)
        total_index_size = sum(table.get('stats', {}).get('index_size_bytes', 0) for table in tables_info.values())

        summary = {
            'dataSize': db_size_bytes,
            'storageSize': db_size_bytes, # For PG, dataSize is a good approximation of storage size
            'indexSize': total_index_size,
            'collections': total_tables, # To match mailer template
            'objects': total_rows, # To match mailer template
            'avgObjSize': (db_size_bytes / total_rows) if total_rows > 0 else 0,
        }

        logger.info("\n" + "="*60)
        logger.info("DATABASE SUMMARY")
        logger.info("="*60)
        logger.info(f"Database Name: {db_name}")
        logger.info(f"Total Database Size: {summary['dataSize'] / (1024*1024):.2f} MB")
        logger.info(f"Total Index Size: {summary['indexSize'] / (1024*1024):.2f} MB")
        logger.info(f"Total Tables: {summary['collections']}")
        logger.info(f"Total Rows: {summary['objects']:,}")
        logger.info("="*60)

        return summary

    except Exception as e:
        logger.error(f"❌ Error getting database summary: {e}")
        return {}

def test_connection() -> bool:
    """Test the database connection."""
    try:
        if engine is None:
            logger.error("❌ Cannot test connection because the database engine is not initialized.")
            return False

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info("✅ Connection successful!")
            logger.info(f"PostgreSQL version: {version}")
            return True
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False

def get_table_details() -> Dict[str, Any]:
    """Retrieve information about all tables in the database."""
    try:
        if engine is None:
            logger.error("❌ Cannot get table details because the database engine is not initialized.")
            return {}

        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        logger.info("="*60)
        logger.info(f"Found {len(table_names)} tables")
        logger.info("="*60)

        tables_info = {}

        with engine.connect() as conn:
            for table_name in table_names:
                logger.info(f"\n📋 Table: {table_name}")
                logger.info("-="*60)

                columns = inspector.get_columns(table_name)
                pk_constraint = inspector.get_pk_constraint(table_name)
                primary_keys = pk_constraint.get('constrained_columns', [])
                foreign_keys = inspector.get_foreign_keys(table_name)
                indexes = inspector.get_indexes(table_name)

                # Get stats
                # Handle potential quoting issues by using parameters or careful formatting, 
                # but inspector names usually are safe-ish. For safety, we quote the table name.
                row_count = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
                # pg_total_relation_size needs a string literal or oid.
                table_size_bytes = conn.execute(text(f"SELECT pg_total_relation_size('{table_name}')")).scalar() or 0
                index_size_bytes = conn.execute(text(f"SELECT pg_indexes_size('{table_name}')")).scalar() or 0


                tables_info[table_name] = {
                    'columns': columns,
                    'primary_keys': primary_keys,
                    'foreign_keys': foreign_keys,
                    'indexes': indexes,
                    'stats': {
                        'count': row_count,
                        'size': table_size_bytes,
                        'avgObjSize': (table_size_bytes / row_count) if row_count > 0 else 0,
                        'index_size_bytes': index_size_bytes,
                    }
                }

                # Display columns
                logger.info(f"Columns ({len(columns)}):")
                for col in columns:
                    pk_marker = " [PK]" if col['name'] in primary_keys else ""
                    nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
                    logger.info(f"  • {col['name']}{pk_marker}: {col['type']} ({nullable})")

                # Display stats
                logger.info("Table Statistics:")
                logger.info(f"  • Rows: {row_count:,}")
                logger.info(f"  • Table Size: {table_size_bytes / (1024*1024):.2f} MB")
                logger.info(f"  • Index Size: {index_size_bytes / (1024*1024):.2f} MB")

        return tables_info

    except Exception as e:
        logger.error(f"❌ Error getting table details: {e}")
        return {}

def main():
    """Main function to run Neon database inspection."""
    logger.info("🔍 Neon Database Inspector")
    logger.info("="*60)

    if engine is None:
        logger.error("❌ Skipping Neon inspection because the database engine is not initialized.")
        logger.warning(
            "⚠️  Make sure 'psycopg2-binary' is installed in the active Python environment.\n"
            "    Run: pip install -r PyCode/requirements.txt"
        )
        return False

    if test_connection():
        db_name = engine.url.database
        tables = get_table_details()
        if tables:
            logger.info(f"✅ Successfully retrieved information for {len(tables)} tables")

            db_summary = get_database_summary(db_name, tables)
            if db_summary:
                logger.info("✅ Database summary generated successfully")

                # Send email report
                logger.info("\n📧 Sending email report to hub@cognerd.ai...")
                with engine.connect() as conn:
                    version_string = conn.execute(text("SELECT version()")).scalar()

                email_sent = send_db_report_email(
                    db_name=f"NeonDB ({db_name})",
                    db_summary=db_summary,
                    collections_info=tables, # The mailer can handle this structure if we match keys
                    mongodb_version=f"PostgreSQL ({version_string.split(',')[0]})",
                    recipient="hub@cognerd.ai"
                )

                if email_sent:
                    logger.info("✅ Email report sent successfully to hub@cognerd.ai")
                else:
                    logger.warning("⚠️  Failed to send email report - check MAILER_EMAIL and MAILER_PASSWORD env vars")
                return True
    else:
        logger.error("❌ Cannot connect to database")
        logger.warning("⚠️  Please update the DATABASE_URL in config/settings.py")
        return False
    return False

if __name__ == "__main__":
    main()
