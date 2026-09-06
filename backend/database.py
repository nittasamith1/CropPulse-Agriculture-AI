"""
CropPulse – MongoDB Database Client Setup
Handles Motor client connections, GridFS setup, automatic database indexing,
and transparent local development persistence fallback if MongoDB Atlas is unreachable.
"""

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from backend.config import settings

import sys
import os
import json
import socket
from datetime import datetime
from urllib.parse import urlparse
import pymongo
import pymongo.errors
from bson import ObjectId


# ── In-Memory / File-Backed Local Development Fallback ────────────────────────
def _matches_filter(doc: dict, flt: dict) -> bool:
    """Helper to match a document against MongoDB-style simple filters."""
    if not flt:
        return True
    for k, v in flt.items():
        if k == "$or" and isinstance(v, list):
            if not any(_matches_filter(doc, sub) for sub in v):
                return False
            continue
        if k == "$and" and isinstance(v, list):
            if not all(_matches_filter(doc, sub) for sub in v):
                return False
            continue
        if isinstance(v, dict):
            doc_val = doc.get(k)
            for op, target in v.items():
                if op == "$eq" and doc_val != target:
                    return False
                elif op == "$ne" and doc_val == target:
                    return False
                elif op == "$gt" and (doc_val is None or doc_val <= target):
                    return False
                elif op == "$gte" and (doc_val is None or doc_val < target):
                    return False
                elif op == "$lt" and (doc_val is None or doc_val >= target):
                    return False
                elif op == "$lte" and (doc_val is None or doc_val > target):
                    return False
                elif op == "$in" and (doc_val not in target if isinstance(target, (list, tuple, set)) else True):
                    return False
                elif op == "$nin" and (doc_val in target if isinstance(target, (list, tuple, set)) else False):
                    return False
            continue
        if doc.get(k) != v:
            return False
    return True


class LocalDevCursor:
    """Async cursor mimicking Motor cursor behavior for local development."""

    def __init__(self, docs: list):
        self.docs = [dict(d) for d in docs]

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            k, direction = key_or_list[0]
        else:
            k = key_or_list
        reverse = (direction == -1 or direction == "desc" or direction == pymongo.DESCENDING)
        self.docs.sort(key=lambda d: str(d.get(k, "") or ""), reverse=reverse)
        return self

    def skip(self, n: int):
        self.docs = self.docs[n:]
        return self

    def limit(self, n: int):
        self.docs = self.docs[:n]
        return self

    async def to_list(self, length=None):
        if length is not None:
            return [dict(d) for d in self.docs[:length]]
        return [dict(d) for d in self.docs]

    def __aiter__(self):
        self._iter = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return dict(next(self._iter))
        except StopIteration:
            raise StopAsyncIteration


class UpdateResult:
    def __init__(self, matched: int = 1, modified: int = 1):
        self.matched_count = matched
        self.modified_count = modified


class DeleteResult:
    def __init__(self, deleted: int = 1):
        self.deleted_count = deleted


class LocalDevCollection:
    """In-memory + file-backed collection replicating Motor async collection methods."""

    def __init__(self, db_store: dict, name: str, persist_fn):
        self.db_store = db_store
        self.name = name
        self.persist_fn = persist_fn

    @property
    def _docs(self) -> list:
        if self.name not in self.db_store:
            self.db_store[self.name] = []
        return self.db_store[self.name]

    async def find_one(self, filter_query: dict = None, projection: dict = None):
        filter_query = filter_query or {}
        for doc in self._docs:
            if _matches_filter(doc, filter_query):
                res = dict(doc)
                if projection and isinstance(projection, dict):
                    # Basic exclusion
                    for pk, pv in projection.items():
                        if pv == 0 and pk in res:
                            del res[pk]
                return res
        return None

    async def replace_one(self, filter_query: dict, replacement: dict, upsert: bool = False):
        replacement = dict(replacement)
        if "_id" not in replacement:
            replacement["_id"] = str(ObjectId())
        for idx, doc in enumerate(self._docs):
            if _matches_filter(doc, filter_query):
                self._docs[idx] = replacement
                self.persist_fn()
                return UpdateResult(1, 1)
        if upsert:
            self._docs.append(replacement)
            self.persist_fn()
            return UpdateResult(0, 1)
        return UpdateResult(0, 0)

    async def update_one(self, filter_query: dict, update: dict):
        set_fields = update.get("$set", update)
        for idx, doc in enumerate(self._docs):
            if _matches_filter(doc, filter_query):
                self._docs[idx].update(set_fields)
                self.persist_fn()
                return UpdateResult(1, 1)
        return UpdateResult(0, 0)

    async def update_many(self, filter_query: dict, update: dict):
        set_fields = update.get("$set", update)
        count = 0
        for idx, doc in enumerate(self._docs):
            if _matches_filter(doc, filter_query):
                self._docs[idx].update(set_fields)
                count += 1
        if count > 0:
            self.persist_fn()
        return UpdateResult(count, count)

    async def delete_one(self, filter_query: dict):
        for idx, doc in enumerate(self._docs):
            if _matches_filter(doc, filter_query):
                del self._docs[idx]
                self.persist_fn()
                return DeleteResult(1)
        return DeleteResult(0)

    def find(self, filter_query: dict = None, projection: dict = None):
        matching = [d for d in self._docs if _matches_filter(d, filter_query or {})]
        return LocalDevCursor(matching)

    async def count_documents(self, filter_query: dict = None):
        if not filter_query:
            return len(self._docs)
        return sum(1 for d in self._docs if _matches_filter(d, filter_query))

    async def create_index(self, keys, **kwargs):
        return "idx_created"

    def aggregate(self, pipeline: list):
        docs = list(self._docs)
        for stage in pipeline:
            if "$match" in stage:
                docs = [d for d in docs if _matches_filter(d, stage["$match"])]
        return LocalDevCursor(docs)


class LocalDevDatabase:
    """Lightweight database holding collections for offline development."""

    def __init__(self, file_path: str = "./tmp/dev_database.json"):
        self.file_path = file_path
        self.store = {}
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.store = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load local dev database file: {e}")
            self.store = {}

    def _persist(self):
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            def json_default(obj):
                if isinstance(obj, (datetime, ObjectId)):
                    return str(obj)
                return str(obj)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.store, f, default=json_default, indent=2)
        except Exception as e:
            logger.warning(f"Could not persist local dev database: {e}")

    def __getitem__(self, collection_name: str) -> LocalDevCollection:
        return LocalDevCollection(self.store, collection_name, self._persist)


class LocalDevGridFSStream:
    def __init__(self, data: bytes, filename: str, metadata: dict):
        self.data = data
        self.filename = filename
        self.metadata = metadata

    async def read(self) -> bytes:
        return self.data


class LocalDevGridFS:
    """Local filesystem-backed GridFS replacement for offline development."""

    def __init__(self, dir_path: str = "./tmp/gridfs_local"):
        self.dir_path = dir_path
        os.makedirs(self.dir_path, exist_ok=True)
        self.meta_file = os.path.join(self.dir_path, "meta.json")
        self.meta = {}
        if os.path.exists(self.meta_file):
            try:
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    self.meta = json.load(f)
            except Exception:
                self.meta = {}

    def _save_meta(self):
        try:
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump(self.meta, f, indent=2)
        except Exception:
            pass

    async def upload_from_stream(self, filename: str, content: bytes, metadata: dict = None):
        file_id = str(ObjectId())
        path = os.path.join(self.dir_path, file_id)
        with open(path, "wb") as f:
            f.write(content)
        self.meta[file_id] = {
            "filename": filename,
            "metadata": metadata or {}
        }
        self._save_meta()
        return ObjectId(file_id)

    async def open_download_stream(self, file_id):
        file_id_str = str(file_id)
        path = os.path.join(self.dir_path, file_id_str)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File {file_id_str} not found in local GridFS")
        with open(path, "rb") as f:
            data = f.read()
        info = self.meta.get(file_id_str, {})
        return LocalDevGridFSStream(data, info.get("filename", "file.dat"), info.get("metadata", {}))

    async def delete(self, file_id):
        file_id_str = str(file_id)
        path = os.path.join(self.dir_path, file_id_str)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        self.meta.pop(file_id_str, None)
        self._save_meta()
        return True


class MockAdmin:
    async def command(self, cmd, *args, **kwargs):
        return {"ok": 1}


class MockClient:
    def __init__(self):
        self.admin = MockAdmin()

    def close(self):
        pass


# ── Database Singleton ────────────────────────────────────────────────────────
class Database:
    """Async database client wrapper for Motor (MongoDB) with local development fallback."""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.gridfs_bucket = None
        self.is_connected = False
        self.is_fallback = False

    @staticmethod
    def diagnose_connection_error(uri: str, error: Exception) -> str:
        """Analyze connection error to distinguish URI, DNS, auth, or network issues."""
        if not (uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")):
            return "Invalid URI: Connection string must start with 'mongodb://' or 'mongodb+srv://'."
        
        host_part = "unknown"
        try:
            if "@" in uri:
                host_part = uri.split("@")[-1].split("/")[0].split("?")[0]
            else:
                scheme_len = len("mongodb+srv://") if uri.startswith("mongodb+srv://") else len("mongodb://")
                host_part = uri[scheme_len:].split("/")[0].split("?")[0]
        except Exception:
            return "Invalid URI: Failed to parse host from connection string."

        dns_host = host_part.split(":")[0]
        is_srv = uri.startswith("mongodb+srv://")

        # 1. DNS check for the primary host
        try:
            socket.gethostbyname(dns_host)
        except socket.gaierror:
            return (
                f"DNS Resolution Failure: Could not resolve hostname '{dns_host}'. "
                "Please check your internet connection and local DNS nameserver settings."
            )

        # 2. SRV DNS lookup check if srv URI
        if is_srv:
            srv_name = f"_mongodb._tcp.{dns_host}"
            try:
                import dns.resolver
                dns.resolver.resolve(srv_name, 'SRV')
            except Exception as dns_err:
                return (
                    f"DNS Resolution Failure (SRV Record): Failed to query SRV record '{srv_name}'. "
                    f"Details: {dns_err}. If you are behind a restrictive network or VPN, SRV queries "
                    "might be blocked by your firewall or DNS provider."
                )

        # 3. Parse specific PyMongo exception details
        err_str = str(error).lower()
        if "auth failed" in err_str or "authentication" in err_str or "login" in err_str or "unauthorized" in err_str:
            return "Authentication Failure: The username or password specified in MONGODB_URI is incorrect."
        
        if "timeout" in err_str or "timed out" in err_str or "serverselectiontimeouterror" in err_str:
            return (
                "Network Timeout: Connection to MongoDB timed out. Verify your firewall rules, "
                "database port access (usually 27017), and MongoDB Atlas IP Access List."
            )

        if isinstance(error, pymongo.errors.ConfigurationError):
            return f"DNS Resolution Failure / Configuration Error: Nameservers failed to resolve the SRV record. Details: {error}"

        return f"Database Connectivity Error: {error}"

    async def connect(self):
        """Establish async connection to MongoDB Atlas or local MongoDB."""
        self.is_connected = False
        self.is_fallback = False
        
        # Override default DNS resolver nameservers if it is an srv URI,
        # to prevent "Server answered REFUSED" errors on restrictive local networks
        uri = settings.MONGODB_URI
        if uri.startswith("mongodb+srv://"):
            try:
                import dns.resolver
                resolver = dns.resolver.get_default_resolver()
                public_dns = ["1.1.1.1", "8.8.8.8"]
                resolver.nameservers = public_dns + [ns for ns in resolver.nameservers if ns not in public_dns]
                logger.info(f"DNS Resolver configured with public fallbacks: {resolver.nameservers}")
            except Exception as dns_err:
                logger.warning(f"Could not configure custom DNS resolver: {dns_err}")

        # Safe host extraction for logging
        host = "unknown"
        try:
            if "@" in uri:
                host = uri.split("@")[-1].split("/")[0].split("?")[0]
            else:
                scheme = "mongodb+srv://" if uri.startswith("mongodb+srv://") else "mongodb://"
                host = uri[len(scheme):].split("/")[0].split("?")[0]
        except Exception:
            pass
            
        logger.info(f"Connecting to MongoDB database host: {host}")
        
        try:
            # Set serverSelectionTimeoutMS to fail fast (5 seconds instead of default 30)
            self.client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.gridfs_bucket = AsyncIOMotorGridFSBucket(self.db)
            
            # Test connectivity
            await self.client.admin.command('ping')
            self.is_connected = True
            self.is_fallback = False
            logger.success("✅ Successfully connected to MongoDB database")
            await self._create_indexes()
        except Exception as e:
            diag_message = self.diagnose_connection_error(settings.MONGODB_URI, e)
            logger.critical(f"❌ DATABASE CONNECTION FAILED:\n{'='*60}\n{diag_message}\n{'='*60}")
            
            if settings.APP_ENV == "production":
                logger.critical("Application shutting down: database connectivity is mandatory in production environment.")
                sys.exit(1)
            else:
                logger.warning(
                    f"⚠️ MongoDB Atlas is unreachable. Initializing Local Storage Fallback for development. "
                    "All registration, login, farms, and predictions will function locally."
                )
                self.client = MockClient()
                self.db = LocalDevDatabase()
                self.gridfs_bucket = LocalDevGridFS()
                self.is_connected = True
                self.is_fallback = True
                await self._create_indexes()
                logger.success("📁 Local storage fallback initialized successfully in ./tmp/dev_database.json")

    async def disconnect(self):
        """Close connection to MongoDB."""
        if self.client and not self.is_fallback:
            self.client.close()
            self.is_connected = False
            logger.info("👋 Disconnected from MongoDB")
        elif self.is_fallback:
            self.is_connected = False
            logger.info("👋 Disconnected from local fallback storage")

    async def _create_indexes(self):
        """Create indexes automatically on startup for performance optimization."""
        logger.info("Creating MongoDB indexes...")
        
        # User collection indexes
        await self.db[settings.COLLECTION_USERS].create_index("email", unique=True)
        await self.db[settings.COLLECTION_USERS].create_index("uid", unique=True)
        
        # Farm collection indexes
        await self.db[settings.COLLECTION_FARMS].create_index("farm_id", unique=True)
        await self.db[settings.COLLECTION_FARMS].create_index("user_id")
        
        # Disease predictions indexes
        await self.db[settings.COLLECTION_DISEASE_PREDICTIONS].create_index("prediction_id", unique=True)
        await self.db[settings.COLLECTION_DISEASE_PREDICTIONS].create_index([("user_id", 1), ("created_at", -1)])
        await self.db[settings.COLLECTION_DISEASE_PREDICTIONS].create_index([("farm_id", 1), ("created_at", -1)])
        await self.db[settings.COLLECTION_DISEASE_PREDICTIONS].create_index("severity")
        
        # Soil predictions indexes
        await self.db[settings.COLLECTION_SOIL_PREDICTIONS].create_index("prediction_id", unique=True)
        await self.db[settings.COLLECTION_SOIL_PREDICTIONS].create_index([("user_id", 1), ("created_at", -1)])
        await self.db[settings.COLLECTION_SOIL_PREDICTIONS].create_index([("farm_id", 1), ("created_at", -1)])
        
        # Weather observations indexes
        await self.db[settings.COLLECTION_WEATHER_OBSERVATIONS].create_index([("latitude", 1), ("longitude", 1)])
        await self.db[settings.COLLECTION_WEATHER_OBSERVATIONS].create_index("created_at")

        # Risk assessments indexes
        await self.db[settings.COLLECTION_RISK_ASSESSMENTS].create_index("assessment_id", unique=True)
        await self.db[settings.COLLECTION_RISK_ASSESSMENTS].create_index([("farm_id", 1), ("created_at", -1)])
        await self.db[settings.COLLECTION_RISK_ASSESSMENTS].create_index("risk_level")

        # Irrigation recommendations indexes
        await self.db[settings.COLLECTION_IRRIGATION_RECOMMENDATIONS].create_index("recommendation_id", unique=True)
        await self.db[settings.COLLECTION_IRRIGATION_RECOMMENDATIONS].create_index([("farm_id", 1), ("created_at", -1)])
        await self.db[settings.COLLECTION_IRRIGATION_RECOMMENDATIONS].create_index("action")

        # Fields collection indexes
        await self.db[settings.COLLECTION_FIELDS].create_index("field_id", unique=True)
        await self.db[settings.COLLECTION_FIELDS].create_index("farm_id")
        
        # Notifications indexes
        await self.db[settings.COLLECTION_NOTIFICATIONS].create_index("notification_id", unique=True)
        await self.db[settings.COLLECTION_NOTIFICATIONS].create_index([("user_id", 1), ("created_at", -1)])
        await self.db[settings.COLLECTION_NOTIFICATIONS].create_index([("user_id", 1), ("read", 1)])
        
        # Reports indexes
        await self.db[settings.COLLECTION_REPORTS].create_index("report_id", unique=True)
        await self.db[settings.COLLECTION_REPORTS].create_index([("user_id", 1), ("created_at", -1)])
        
        # Refresh tokens & reset tokens
        await self.db[settings.COLLECTION_REFRESH_TOKENS].create_index("token", unique=True)
        await self.db[settings.COLLECTION_REFRESH_TOKENS].create_index("expires_at", expireAfterSeconds=0)
        
        await self.db[settings.COLLECTION_RESET_TOKENS].create_index("token", unique=True)
        await self.db[settings.COLLECTION_RESET_TOKENS].create_index("expires_at", expireAfterSeconds=0)
        
        logger.success("✅ MongoDB indexes created successfully")


db = Database()


def get_database():
    """Dependency helper to get database instance."""
    return db.db


def get_gridfs():
    """Dependency helper to get GridFS bucket."""
    return db.gridfs_bucket
