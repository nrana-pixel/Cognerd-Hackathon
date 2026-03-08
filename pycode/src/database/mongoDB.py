"""
MONGODB DATABASE CONNECTION AND COLLECTION INSPECTOR
This script connects to a MongoDB database and retrieves comprehensive
information about all collections, including their structure, indexes, and data.

It also contains the repository logic for storing and retrieving blog data.

Created by: Aman Mundra
Date: 2026-02-04
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from config.settings import Config
from utils.log_utils import get_logger
from utils.mailer import send_db_report_email

# Initialize logger
logger = get_logger("mongo_inspector")

# Database connection logic
if Config.MONGODB_URI:
    client = MongoClient(Config.MONGODB_URI, connect=False)
    database = client[Config.MONGODB_DB]
    blogs_collection = database[Config.MONGODB_COLLECTION]
else:
    logger.warning("MONGODB_URI not set; using in-memory Mongo repository. Data will not persist.")
    
    class _InMemoryCollection:
        """Very small subset of pymongo Collection API for local/dev use."""

        class _InsertOneResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id

        def __init__(self):
            self._documents = []

        @staticmethod
        def _matches(doc, filter_dict):
            for key, value in filter_dict.items():
                if key == "_id":
                    if str(doc.get("_id")) != str(value):
                        return False
                    continue
                if doc.get(key) != value:
                    return False
            return True

        def find_one(self, filter_dict=None, *, sort=None):
            filter_dict = filter_dict or {}
            documents = [doc for doc in self._documents if self._matches(doc, filter_dict)]
            if sort:
                key, direction = sort[0]
                reverse = direction == -1
                documents.sort(key=lambda d: d.get(key), reverse=reverse)
            return documents[0] if documents else None

        def insert_one(self, doc):
            new_doc = doc.copy()
            new_doc.setdefault("_id", ObjectId())
            self._documents.append(new_doc)
            return self._InsertOneResult(new_doc["_id"])

        def update_one(self, filter_dict, update_dict):
            doc = self.find_one(filter_dict)
            if not doc:
                return
            set_values = update_dict.get("$set", {})
            doc.update(set_values)
            
    client = None
    database = None
    blogs_collection = _InMemoryCollection()




LOCAL_TIMEZONE_NAME = os.getenv("LOCAL_TIMEZONE", "Asia/Kolkata")
try:
    LOCAL_TIMEZONE = ZoneInfo(LOCAL_TIMEZONE_NAME)
except ZoneInfoNotFoundError:
    LOCAL_TIMEZONE = timezone(timedelta(hours=5, minutes=30))
    LOCAL_TIMEZONE_NAME = "UTC+05:30"


JsonEntry = Dict[str, Any]
TopicEntry = Dict[str, Any]
TopicDoc = Dict[str, List[TopicEntry]]


class TopicSource:
    USER = "user"
    AI_SUGGESTION = "ai_suggestions"
    BRAND_PROMPT = "prompt"


TOPIC_SOURCES = (TopicSource.USER, TopicSource.AI_SUGGESTION, TopicSource.BRAND_PROMPT)


def _local_now() -> datetime:
    return datetime.now(tz=LOCAL_TIMEZONE)


def _now_iso() -> str:
    return _local_now().isoformat()


def _ensure_entries(items: Optional[List[JsonEntry]]) -> List[JsonEntry]:
    if not items:
        return []
    normalized: List[JsonEntry] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(item)
    return normalized


def _normalize_topic_source(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"user", "users"}:
        return TopicSource.USER
    if normalized in {"ai", "ai_suggestion", "ai_suggestions", "suggestion", "suggestions"}:
        return TopicSource.AI_SUGGESTION
    if normalized in {"prompt", "prompts", "brand_prompt", "brand"}:
        return TopicSource.BRAND_PROMPT
    return normalized or None


def _make_topic_entry(
    topic: Optional[str],
    *,
    source: Optional[str],
    timestamp: Optional[str] = None,
) -> Optional[TopicEntry]:
    if not topic:
        return None
    normalized_source = _normalize_topic_source(source) or TopicSource.USER
    return {
        "topic": topic,
        "timestamp": timestamp or _now_iso(),
        "source": normalized_source,
    }


def _topic_entry_key(entry: TopicEntry) -> tuple:
    return (
        (entry.get("topic") or "").strip().lower(),
        entry.get("source") or TopicSource.USER,
    )


def _append_topic_entry(
    entries: List[TopicEntry],
    *,
    topic: Optional[str],
    source: Optional[str],
    timestamp: Optional[str] = None,
) -> bool:
    entry = _make_topic_entry(topic, source=source, timestamp=timestamp)
    if not entry:
        return False
    key = _topic_entry_key(entry)
    for existing in entries:
        if _topic_entry_key(existing) == key:
            return False
    entries.append(entry)
    return True


def _ensure_topic_entries(
    raw_topics,
    *,
    blog_id: Optional[str] = None,
) -> List[TopicEntry]:
    entries: List[TopicEntry] = []
    changed = False

    def _consume(value, default_source=None):
        nonlocal changed
        if isinstance(value, dict):
            topic_value = value.get("topic") or value.get("content")
            timestamp = value.get("timestamp")
            source_value = _normalize_topic_source(value.get("source")) or default_source
            if not source_value and value.get("is_prompt") is not None:
                source_value = TopicSource.BRAND_PROMPT if str(value.get("is_prompt")).lower() == "true" else TopicSource.USER
        else:
            topic_value = value
            timestamp = None
            source_value = default_source
        source_value = source_value or TopicSource.USER
        inserted = _append_topic_entry(entries, topic=topic_value, source=source_value, timestamp=timestamp)
        if not inserted:
            changed = changed or isinstance(value, (dict, list))
        if isinstance(value, dict) and value.get("source") != source_value:
            changed = True

    if isinstance(raw_topics, dict):
        changed = True
        for source_key, values in raw_topics.items():
            normalized_source = _normalize_topic_source(source_key) or TopicSource.USER
            value_list = values if isinstance(values, list) else [values]
            for entry in value_list:
                _consume(entry, default_source=normalized_source)
    elif isinstance(raw_topics, list):
        for entry in raw_topics:
            _consume(entry)
    elif raw_topics:
        _consume(raw_topics)
        changed = True

    if changed and blog_id:
        blogs_collection.update_one(
            {"_id": _ensure_object_id(blog_id)},
            {"$set": {"topic": entries}},
        )

    return entries


def _make_entry(
    content: Optional[str],
    *,
    timestamp: Optional[str] = None,
    topic: Optional[str] = None,
    is_prompt: Optional[str] = None,
) -> Optional[JsonEntry]:
    if content is None:
        return None
    entry: JsonEntry = {
        "content": content,
        "timestamp": timestamp or _now_iso(),
    }
    if topic is not None:
        entry["topic"] = topic
    if is_prompt is not None:
        entry["is_prompt"] = is_prompt
    return entry


def _serialize(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    serialized = doc.copy()
    serialized["id"] = str(serialized.pop("_id"))
    created_at = serialized.get("created_at")
    if isinstance(created_at, datetime):
        serialized["created_at"] = created_at.astimezone(LOCAL_TIMEZONE).isoformat()
    elif not created_at:
        serialized["created_at"] = _now_iso()
    serialized["topic"] = _ensure_topic_entries(serialized.get("topic"), blog_id=serialized["id"])
    return serialized


def _ensure_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as exc:
        raise ValueError(f"Invalid blog id: {value}") from exc


def get_blog_by_user_and_company(*, user_id: str, brand_url: str) -> Optional[Dict[str, Any]]:
    doc = blogs_collection.find_one(
        {"user_id": user_id, "brand_url": brand_url},
        sort=[("created_at", -1)]
    )
    return _serialize(doc)


def create_blog_entry(
    *,
    user_id: str,
    topic: Optional[str],
    brand_url: str,
    email_id: Optional[str] = None,
    brand_name: Optional[str] = None,
    brand_industry: Optional[str] = None,
    brand_location: Optional[str] = None,
    blog: Optional[str] = None,
    status: str = "PENDING",
    twitter_post: Optional[str] = None,
    linkedin_post: Optional[str] = None,
    reddit_post: Optional[str] = None,
    is_prompt: str = "false",
    timestamp: Optional[str] = None,
    topic_source: str = "user",
) -> Dict[str, Any]:
    doc: Dict[str, Any] = {
        "user_id": user_id,
        "brand_url": brand_url,
        "email_id": email_id,
        "brand_name": brand_name,
        "brand_industry": brand_industry,
        "brand_location": brand_location,
        "status": status,
        "created_at": _now_iso(),
        "blogs": [],
        "topic": [],
        "twitter_post": [],
        "linkedin_post": [],
        "reddit_post": [],
    }

    _append_topic_entry(doc["topic"], topic=topic, source=topic_source, timestamp=timestamp)

    blog_entry = _make_entry(blog, timestamp=timestamp, topic=topic, is_prompt=is_prompt)
    if blog_entry:
        doc["blogs"].append(blog_entry)

    for field, value in (
        ("twitter_post", twitter_post),
        ("linkedin_post", linkedin_post),
        ("reddit_post", reddit_post),
    ):
        if value:
            entry = _make_entry(value, timestamp=timestamp, topic=topic)
            if entry:
                doc[field].append(entry)

    result = blogs_collection.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc["topic"] = _ensure_topic_entries(doc.get("topic"), blog_id=doc["id"])
    return doc


def get_or_create_blog_entry(
    *,
    user_id: str,
    brand_url: str,
    topic: str,
    email_id: Optional[str] = None,
    brand_name: Optional[str] = None,
    brand_industry: Optional[str] = None,
    brand_location: Optional[str] = None,
    is_prompt: str = "false",
    timestamp: Optional[str] = None,
    topic_source: str = "user",
) -> Dict[str, Any]:
    existing = get_blog_by_user_and_company(user_id=user_id, brand_url=brand_url)
    if existing:
        updates: Dict[str, Any] = {}
        if email_id and not existing.get("email_id"):
            updates["email_id"] = email_id
        if brand_name and not existing.get("brand_name"):
            updates["brand_name"] = brand_name
        if brand_industry and not existing.get("brand_industry"):
            updates["brand_industry"] = brand_industry
        if brand_location and not existing.get("brand_location"):
            updates["brand_location"] = brand_location

        topic_entries = _ensure_topic_entries(existing.get("topic"), blog_id=existing["id"])
        if topic:
            inserted = _append_topic_entry(topic_entries, topic=topic, source=topic_source, timestamp=timestamp)
            if inserted:
                updates["topic"] = topic_entries

        if updates:
            blogs_collection.update_one(
                {"_id": _ensure_object_id(existing["id"])},
                {"$set": updates}
            )
            existing.update(updates)
        existing["topic"] = updates.get("topic", topic_entries)
        return existing

    return create_blog_entry(
        user_id=user_id,
        topic=topic,
        brand_url=brand_url,
        email_id=email_id,
        brand_name=brand_name,
        brand_industry=brand_industry,
        brand_location=brand_location,
        status="PENDING",
        is_prompt=is_prompt,
        timestamp=timestamp,
        topic_source=topic_source,
    )


def get_blog_by_id(blog_id: str) -> Optional[Dict[str, Any]]:
    try:
        object_id = ObjectId(blog_id)
    except Exception:
        return None
    doc = blogs_collection.find_one({"_id": object_id})
    return _serialize(doc)


def _append_entry(list_value: List[JsonEntry], entry: Optional[JsonEntry]) -> List[JsonEntry]:
    if entry:
        list_value = _ensure_entries(list_value)
        list_value.append(entry)
    return list_value


def update_blog_status(
    blog_id: str,
    *,
    status: str,
    blog_content: Optional[str] = None,
    topic: Optional[str] = None,
    is_prompt: str = "false",
    timestamp: Optional[str] = None,
    topic_source: str = "user",
) -> Optional[Dict[str, Any]]:
    doc = get_blog_by_id(blog_id)
    if not doc:
        raise ValueError(f"Blog with id {blog_id} not found")

    blogs = _ensure_entries(doc.get("blogs"))
    if blog_content is not None:
        blogs = _append_entry(blogs, _make_entry(blog_content, timestamp=timestamp, topic=topic, is_prompt=is_prompt))

    topic_entries = _ensure_topic_entries(doc.get("topic"), blog_id=blog_id)
    if topic:
        inserted = _append_topic_entry(topic_entries, topic=topic, source=topic_source, timestamp=timestamp)
        if inserted:
            doc["topic"] = topic_entries

    update_fields = {
        "status": status,
        "blogs": blogs,
        "topic": topic_entries,
    }
    blogs_collection.update_one(
        {"_id": _ensure_object_id(blog_id)},
        {"$set": update_fields}
    )

    doc.update(update_fields)
    return doc


def _ensure_blog_document(
    *,
    user_id: str,
    brand_url: str,
    email_id: Optional[str] = None,
    brand_name: Optional[str] = None,
    brand_industry: Optional[str] = None,
    brand_location: Optional[str] = None,
) -> Dict[str, Any]:
    existing = get_blog_by_user_and_company(user_id=user_id, brand_url=brand_url)
    if existing:
        existing["topic"] = _ensure_topic_entries(existing.get("topic"), blog_id=existing["id"])
        return existing
    return create_blog_entry(
        user_id=user_id,
        topic=None,
        topic_source=TopicSource.USER,
        brand_url=brand_url,
        email_id=email_id,
        brand_name=brand_name,
        brand_industry=brand_industry,
        brand_location=brand_location,
        status="PENDING",
    )


def append_topics_metadata(
    *,
    user_id: str,
    brand_url: str,
    topics: List[str],
    source: str,
    timestamp: Optional[str] = None,
    email_id: Optional[str] = None,
    brand_name: Optional[str] = None,
    brand_industry: Optional[str] = None,
    brand_location: Optional[str] = None,
) -> Dict[str, Any]:
    doc = _ensure_blog_document(
        user_id=user_id,
        brand_url=brand_url,
        email_id=email_id,
        brand_name=brand_name,
        brand_industry=brand_industry,
        brand_location=brand_location,
    )
    topic_entries = _ensure_topic_entries(doc.get("topic"), blog_id=doc["id"])
    dirty = False
    for topic in topics:
        if _append_topic_entry(topic_entries, topic=topic, source=source, timestamp=timestamp):
            dirty = True
    if dirty:
        blogs_collection.update_one(
            {"_id": _ensure_object_id(doc["id"])},
            {"$set": {"topic": topic_entries}},
        )
        doc["topic"] = topic_entries
    return doc


def append_social_post(
    blog_id: str,
    *,
    platform: str,
    content: str,
    topic: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    doc = get_blog_by_id(blog_id)
    if not doc:
        raise ValueError(f"Blog with id {blog_id} not found")

    platform = platform.lower()
    field_map = {
        "twitter": "twitter_post",
        "linkedin": "linkedin_post",
        "reddit": "reddit_post",
    }
    field = field_map.get(platform)
    if not field:
        raise ValueError(f"Unsupported platform for saving: {platform}")

    entries = _ensure_entries(doc.get(field))
    if topic:
        entries = [entry for entry in entries if entry.get("topic") != topic]

    new_entry = _make_entry(content, timestamp=timestamp, topic=topic)
    if new_entry:
        entries.append(new_entry)

    blogs_collection.update_one(
        {"_id": _ensure_object_id(blog_id)},
        {"$set": {field: entries}}
    )

    doc[field] = entries
    return doc


# Inspector Functions
def get_database_summary(db):
    """Get comprehensive database statistics and summary."""
    try:
        # Get database stats
        db_stats = db.command("dbStats")

        # Extract key metrics
        total_size = db_stats.get('dataSize', 0)
        storage_size = db_stats.get('storageSize', 0)
        index_size = db_stats.get('indexSize', 0)
        total_size_with_indexes = total_size + index_size
        num_collections = db_stats.get('collections', 0)
        num_objects = db_stats.get('objects', 0)
        avg_obj_size = db_stats.get('avgObjSize', 0)

        # Convert to MB/GB
        total_size_mb = total_size / (1024 * 1024)
        storage_size_mb = storage_size / (1024 * 1024)
        index_size_mb = index_size / (1024 * 1024)
        total_with_indexes_mb = total_size_with_indexes / (1024 * 1024)
        avg_obj_kb = avg_obj_size / 1024

        # Display summary
        logger.info("\n" + "="*60)
        logger.info("DATABASE SUMMARY")
        logger.info("="*60)
        logger.info(f"Database Name: {db.name}")
        logger.info(f"MongoDB Version: {db.client.server_info().get('version', 'unknown')}")
        logger.info("")
        logger.info("Storage Statistics:")
        logger.info(f"  â€¢ Total Data Size: {total_size_mb:.2f} MB ({total_size:,} bytes)")
        logger.info(f"  â€¢ Storage Size: {storage_size_mb:.2f} MB ({storage_size:,} bytes)")
        logger.info(f"  â€¢ Index Size: {index_size_mb:.2f} MB ({index_size:,} bytes)")
        logger.info(f"  â€¢ Total Size (Data + Indexes): {total_with_indexes_mb:.2f} MB")
        logger.info("")
        logger.info("Collection Statistics:")
        logger.info(f"  â€¢ Total Collections: {num_collections:,}")
        logger.info(f"  â€¢ Total Documents: {num_objects:,}")
        logger.info(f"  â€¢ Average Document Size: {avg_obj_kb:.2f} KB ({avg_obj_size:,} bytes)")
        logger.info("")

        # Calculate space efficiency
        if storage_size > 0:
            efficiency = (total_size / storage_size) * 100
            logger.info(f"Storage Efficiency: {efficiency:.1f}%")

        logger.info("="*60)

        return db_stats

    except Exception as e:
        logger.error(f"âŒ Error getting database summary: {e}")
        return None


def test_connection(client_obj):
    """Test the database connection."""
    try:
        # The ping command is cheap and does not require auth
        client_obj.admin.command('ping')

        # Get server info
        server_info = client_obj.server_info()
        logger.info("âœ… Connection successful!")
        logger.info(f"MongoDB version: {server_info.get('version', 'unknown')}")
        logger.info(f"Server: {client_obj.address[0]}:{client_obj.address[1]}")
        return True
    except ConnectionFailure as e:
        logger.error(f"âŒ Connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"âŒ Error: {e}")
        return False
    
def get_collection_details(db):
    """Retrieve information about all collections in the database."""
    try:
        collection_names = db.list_collection_names()

        logger.info("="*60)
        logger.info(f"Connected to Database: {db.name}")
        logger.info("="*60)
        logger.info(f"Found {len(collection_names)} collections")

        collections_info = {}

        for collection_name in collection_names:
            collection = db[collection_name]
            logger.info(f"\nðŸ“‹ Collection: {collection_name}")
            logger.info("-" * 60)

            # Get indexes
            indexes = list(collection.list_indexes())

            # Get sample document to show structure
            sample_doc = collection.find_one()

            # Get collection stats
            stats = db.command("collStats", collection_name)

            collections_info[collection_name] = {
                'indexes': indexes,
                'sample_document': sample_doc,
                'stats': stats
            }

            # Display document structure from sample
            if sample_doc:
                logger.info("Document Structure (from sample):")
                for key, value in sample_doc.items():
                    value_type = type(value).__name__
                    logger.info(f"  â€¢ {key}: {value_type}")
            else:
                logger.info("No documents found in this collection")

            # Display indexes
            if indexes:
                logger.info(f"Indexes ({len(indexes)}):")
                for idx in indexes:
                    keys = idx.get('key', {})
                    unique = " (UNIQUE)" if idx.get('unique', False) else ""
                    name = idx.get('name', 'unnamed')
                    logger.info(f"  â€¢ {name}{unique}: {dict(keys)}")

            # Display collection stats (convert to MB)
            size_bytes = stats.get('size', 0)
            storage_bytes = stats.get('storageSize', 0)
            avg_doc_bytes = stats.get('avgObjSize', 0)

            size_mb = size_bytes / (1024 * 1024)
            storage_mb = storage_bytes / (1024 * 1024)
            avg_doc_kb = avg_doc_bytes / 1024

            logger.info("Collection Statistics:")
            logger.info(f"  â€¢ Size: {size_mb:.2f} MB ({size_bytes:,} bytes)")
            logger.info(f"  â€¢ Storage Size: {storage_mb:.2f} MB ({storage_bytes:,} bytes)")
            logger.info(f"  â€¢ Average Document Size: {avg_doc_kb:.2f} KB ({avg_doc_bytes:,} bytes)")

        # Get document counts
        logger.info("="*60)
        logger.info("Collection Document Counts:")
        logger.info("="*60)
        for collection_name in collection_names:
            count = db[collection_name].count_documents({})
            logger.info(f"  {collection_name}: {count:,} documents")

        logger.info("="*60)
        return collections_info

    except Exception as e:
        logger.error(f"âŒ Error: {e}")
        return None


def main():
    """Main function to run MongoDB database inspection."""
    logger.info("ðŸ” MongoDB Database Inspector")
    logger.info("="*60)

    try:
        # Create MongoDB client
        # Use the global client if available, else create a new one for inspection
        if client:
             inspection_client = client
        else:
             inspection_client = MongoClient(Config.MONGODB_URI, connect=False)

        if test_connection(inspection_client):
            # Get database name from URL or use default
            db_name = Config.MONGODB_DB
            if not db_name or db_name == '':
                logger.warning("âš ï¸  No database specified in URL, using 'test' database")
                db_name = 'test'

            db = inspection_client[db_name]
            collections = get_collection_details(db)
            if collections:
                logger.info(f"âœ… Successfully retrieved information for {len(collections)} collections")

                # Get and display database summary
                db_summary = get_database_summary(db)
                if db_summary:
                    logger.info("âœ… Database summary generated successfully")

                    # Send email report
                    mongodb_version = db.client.server_info().get('version', 'unknown')
                    logger.info("\nðŸ“§ Sending email report to hub@cognerd.ai...")
                    email_sent = send_db_report_email(
                        db_name=db_name,
                        db_summary=db_summary,
                        collections_info=collections,
                        mongodb_version=mongodb_version,
                        recipient="hub@cognerd.ai"
                    )

                    if email_sent:
                        logger.info("âœ… Email report sent successfully to hub@cognerd.ai")
                    else:
                        logger.warning("âš ï¸  Failed to send email report - check MAILER_EMAIL and MAILER_PASSWORD env vars")

                return True
        else:
            logger.error("âŒ Cannot connect to database")
            logger.warning("âš ï¸  Please update the MONGO_URL in config/settings.py")
            return False

        # Do not close the global client if it is shared
        if inspection_client != client:
            inspection_client.close()
            
        logger.info("MongoDB client inspection completed")
        return True

    except Exception as e:
        logger.error(f"âŒ Failed to initialize MongoDB client: {e}")
        logger.warning("âš ï¸  Please update the MONGO_URL in config/settings.py")
        return False


if __name__ == "__main__":
    main()
