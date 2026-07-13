from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from gi.repository import GLib

from dealwise.data.database import DatabaseManager
from dealwise.models import MarketplaceListing
from dealwise.services.active_build import ActiveBuildService
from dealwise.services.product_classifier import ProductClassifier, ProductClassification
from dealwise.services.source_adapters import SourceAdapterRegistry, SourceSearchRequest, SourceSearchResult


@dataclass(slots=True)
class HuntSessionStats:
    session_id: str
    status: str
    active_parts: list[str]
    generated_queries: list[str]
    raw_found: int = 0
    validated: int = 0
    rejected: int = 0
    duplicates: int = 0
    failed_sources: int = 0
    cached_results: int = 0
    source_lines: list[str] = field(default_factory=list)


class ActiveHuntSessionService:
    """Session/cache/classification foundation for the Active Hunt workflow."""

    RULE_VERSION = "0.8.3"

    def __init__(self, database: DatabaseManager, active_build_service: ActiveBuildService) -> None:
        self.database = database
        self.active_build_service = active_build_service
        self.classifier = ProductClassifier()
        self.sources = SourceAdapterRegistry()
        self._cancel_event = threading.Event()
        self._current_stats: HuntSessionStats | None = None
        self._lock = threading.RLock()
        self.ensure_schema()

    def ensure_schema(self) -> None:
        with self.database.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS search_sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    active_parts_json TEXT NOT NULL DEFAULT '[]',
                    generated_queries_json TEXT NOT NULL DEFAULT '[]',
                    raw_result_count INTEGER NOT NULL DEFAULT 0,
                    filtered_result_count INTEGER NOT NULL DEFAULT 0,
                    accepted_result_count INTEGER NOT NULL DEFAULT 0,
                    duplicate_count INTEGER NOT NULL DEFAULT 0,
                    failed_source_count INTEGER NOT NULL DEFAULT 0,
                    cached_result_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS search_session_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    raw_count INTEGER NOT NULL DEFAULT 0,
                    accepted_count INTEGER NOT NULL DEFAULT 0,
                    rejected_count INTEGER NOT NULL DEFAULT 0,
                    duplicate_count INTEGER NOT NULL DEFAULT 0,
                    elapsed_ms INTEGER NOT NULL DEFAULT 0,
                    assisted_url TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS raw_search_cache (
                    cache_key TEXT PRIMARY KEY,
                    source_name TEXT NOT NULL,
                    query TEXT NOT NULL,
                    page INTEGER NOT NULL DEFAULT 1,
                    filter_json TEXT NOT NULL DEFAULT '{}',
                    response_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS listing_classifications (
                    fingerprint TEXT PRIMARY KEY,
                    listing_key TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL,
                    source_name TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL,
                    bucket TEXT NOT NULL,
                    identity_confidence INTEGER NOT NULL,
                    matched_model TEXT NOT NULL DEFAULT '',
                    extracted_spec TEXT NOT NULL DEFAULT '',
                    rejection_reason TEXT NOT NULL DEFAULT '',
                    deal_score_cap INTEGER,
                    evidence_score INTEGER NOT NULL DEFAULT 0,
                    scam_risk REAL NOT NULL DEFAULT 0,
                    rule_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS listing_rejections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    title TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS listing_fingerprints (
                    fingerprint TEXT PRIMARY KEY,
                    source_name TEXT NOT NULL,
                    external_id TEXT NOT NULL DEFAULT '',
                    canonical_url TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    price REAL,
                    postage TEXT NOT NULL DEFAULT '',
                    seller TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_status (
                    source_name TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    last_checked_at TEXT NOT NULL,
                    message TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS generated_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    part_type TEXT NOT NULL,
                    query TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_classification_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    title TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )
            connection.commit()

    def start_session(self) -> HuntSessionStats:
        self._cancel_event.clear()
        plan = self.active_build_service.active_search_plan()
        session_id = str(uuid4())
        active_parts = sorted(plan.queries_by_part)
        generated_queries = plan.all_queries()
        now = datetime.now(timezone.utc).isoformat()

        stats = HuntSessionStats(
            session_id=session_id,
            status="Searching",
            active_parts=active_parts,
            generated_queries=generated_queries,
            source_lines=["Starting Active Hunt..."],
        )

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO search_sessions (
                    session_id,
                    started_at,
                    status,
                    active_parts_json,
                    generated_queries_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    now,
                    "Searching",
                    json.dumps(active_parts),
                    json.dumps(generated_queries),
                ),
            )

            for part, queries in plan.queries_by_part.items():
                for query in queries:
                    connection.execute(
                        """
                        INSERT INTO generated_queries (
                            session_id,
                            part_type,
                            query,
                            created_at
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (session_id, part, query, now),
                    )

            connection.commit()

        with self._lock:
            self._current_stats = stats

        return stats

    def cancel(self) -> None:
        self._cancel_event.set()

        with self._lock:
            if self._current_stats is not None:
                self._current_stats.status = "Cancelled"
                self._finish_session(self._current_stats)

    def current_stats(self) -> HuntSessionStats | None:
        with self._lock:
            return self._current_stats

    def classify_listing(
        self,
        listing: MarketplaceListing,
        category_hint: str = "",
    ) -> ProductClassification:
        fingerprint = self.fingerprint_for_listing(listing)
        cached = self._read_cached_classification(fingerprint)

        if cached is not None:
            return cached

        classification = self.classifier.classify(
            title=listing.title,
            source_query=listing.source_query or "",
            category_hint=category_hint,
            description=json.dumps(listing.raw, sort_keys=True) if listing.raw else "",
        )
        self._store_classification(fingerprint, listing, classification)
        return classification

    def fingerprint_for_listing(self, listing: MarketplaceListing) -> str:
        payload = "|".join(
            [
                listing.marketplace.lower().strip(),
                listing.id.lower().strip(),
                listing.url.lower().strip(),
                listing.title.lower().strip(),
                str(listing.price or ""),
                listing.seller_name or "",
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def record_source_result(self, session_id: str, result: SourceSearchResult) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO search_session_sources (
                    session_id,
                    source_name,
                    status,
                    raw_count,
                    accepted_count,
                    rejected_count,
                    duplicate_count,
                    elapsed_ms,
                    assisted_url,
                    error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    result.source_name,
                    result.status,
                    result.raw_count,
                    result.accepted_count,
                    result.rejected_count,
                    result.duplicate_count,
                    result.elapsed_ms,
                    result.assisted_url,
                    result.error,
                ),
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO source_status (
                    source_name,
                    status,
                    last_checked_at,
                    message
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    result.source_name,
                    result.status,
                    datetime.now(timezone.utc).isoformat(),
                    result.error or result.assisted_url,
                ),
            )
            connection.commit()

    def source_status_lines(self) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT source_name, status, message
                FROM source_status
                ORDER BY source_name
                """
            ).fetchall()

        if not rows:
            return ["Source status will appear after the first Active Hunt."]

        lines: list[str] = []

        for row in rows:
            message = str(row["message"] or "")
            suffix = f" — {message}" if message else ""
            lines.append(f"{row['source_name']}: {row['status']}{suffix}")

        return lines

    def _read_cached_classification(self, fingerprint: str) -> ProductClassification | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM listing_classifications
                WHERE fingerprint = ?
                  AND rule_version = ?
                """,
                (fingerprint, self.RULE_VERSION),
            ).fetchone()

        if row is None:
            return None

        return ProductClassification(
            category=str(row["category"]),
            bucket=str(row["bucket"]),
            identity_confidence=int(row["identity_confidence"]),
            matched_model=str(row["matched_model"] or ""),
            extracted_spec=str(row["extracted_spec"] or ""),
            rejection_reason=str(row["rejection_reason"] or ""),
            deal_score_cap=row["deal_score_cap"],
            evidence_score=int(row["evidence_score"] or 0),
            scam_risk=float(row["scam_risk"] or 0),
            why=["Loaded cached classification."],
        )

    def _store_classification(
        self,
        fingerprint: str,
        listing: MarketplaceListing,
        classification: ProductClassification,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO listing_classifications (
                    fingerprint,
                    listing_key,
                    title,
                    source_name,
                    category,
                    bucket,
                    identity_confidence,
                    matched_model,
                    extracted_spec,
                    rejection_reason,
                    deal_score_cap,
                    evidence_score,
                    scam_risk,
                    rule_version,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM listing_classifications WHERE fingerprint = ?), ?), ?)
                """,
                (
                    fingerprint,
                    listing.dedupe_key,
                    listing.title,
                    listing.marketplace,
                    classification.category,
                    classification.bucket,
                    classification.identity_confidence,
                    classification.matched_model,
                    classification.extracted_spec,
                    classification.rejection_reason,
                    classification.deal_score_cap,
                    classification.evidence_score,
                    classification.scam_risk,
                    self.RULE_VERSION,
                    fingerprint,
                    now,
                    now,
                ),
            )

            if not classification.is_deal_candidate:
                connection.execute(
                    """
                    INSERT INTO listing_rejections (
                        fingerprint,
                        title,
                        reason,
                        created_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        fingerprint,
                        listing.title,
                        classification.rejection_reason or classification.bucket,
                        now,
                    ),
                )

            connection.execute(
                """
                INSERT OR REPLACE INTO listing_fingerprints (
                    fingerprint,
                    source_name,
                    external_id,
                    canonical_url,
                    title,
                    price,
                    postage,
                    seller,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, '', ?, ?)
                """,
                (
                    fingerprint,
                    listing.marketplace,
                    listing.id,
                    listing.url,
                    listing.title,
                    listing.price,
                    listing.seller_name or "",
                    now,
                ),
            )

            connection.commit()

    def _finish_session(self, stats: HuntSessionStats) -> None:
        ended_at = datetime.now(timezone.utc).isoformat()

        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE search_sessions
                SET
                    ended_at = ?,
                    status = ?,
                    raw_result_count = ?,
                    filtered_result_count = ?,
                    accepted_result_count = ?,
                    duplicate_count = ?,
                    failed_source_count = ?,
                    cached_result_count = ?
                WHERE session_id = ?
                """,
                (
                    ended_at,
                    stats.status,
                    stats.raw_found,
                    stats.validated + stats.rejected,
                    stats.validated,
                    stats.duplicates,
                    stats.failed_sources,
                    stats.cached_results,
                    stats.session_id,
                ),
            )
            connection.commit()
