import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from database.processed_database import ProcessedDatabase

SEASONAL_CYCLE_WEEKS = 3

# content type reuse policies
CONTENT_POLICIES: dict[str, dict[str, Any]] = {
    "deal": {"can_reuse": False, "cooldown_days": 0, "max_used_count": 0},
    "guide": {"can_reuse": True, "cooldown_days": 90, "max_used_count": 3},
    "experience": {
        "can_reuse": True,
        "cooldown_days": 120,
        "max_used_count": 2,
    },
    "tip": {"can_reuse": True, "cooldown_days": 60, "max_used_count": 3},
    "news": {"can_reuse": True, "cooldown_days": 180, "max_used_count": 1},
}

SEASONS: dict[str, list[int]] = {
    "winter": [12, 1, 2],
    "spring": [3, 4, 5],
    "summer": [6, 7, 8],
    "fall": [9, 10, 11],
}

SEASON_ORDER = list(SEASONS.keys())


def _current_season(month: int) -> str:
    return next(
        (s for s, months in SEASONS.items() if month in months),
        "any",
    )


def _next_season(current: str) -> str:
    idx = SEASON_ORDER.index(current)
    return SEASON_ORDER[(idx + 1) % len(SEASON_ORDER)]


def _freshness_clause(content_type: str) -> tuple[str, list]:
    policy = CONTENT_POLICIES.get(
        content_type,
        {"can_reuse": True, "cooldown_days": 30, "max_used_count": 3},
    )

    if not policy["can_reuse"]:
        return "AND (last_used IS NULL)", []

    return (
        "AND ("
        "  last_used IS NULL"
        "  OR ("
        "    datetime(last_used, '+' || ? || ' days') < datetime('now')"
        "    AND COALESCE(used_count, 0) < ?"
        "  )"
        ")",
        [policy["cooldown_days"], policy["max_used_count"]],
    )


def _exclude_ids_clause(
    ids: list[int],
) -> tuple[str, list]:
    if not ids:
        return "", []
    return (
        "AND id NOT IN (SELECT value FROM json_each(?))",
        [json.dumps(ids)],
    )


def _in_clause(ids: list[int]) -> tuple[str, list]:
    if not ids:
        return "(0)", []
    return (
        "(SELECT value FROM json_each(?))",
        [json.dumps(ids)],
    )


def _extract_location(locations_json: str | dict) -> str:
    try:
        locations = (
            json.loads(locations_json)
            if isinstance(locations_json, str)
            else locations_json
        )
        if locations:
            return locations.get("primary", "").lower()
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass
    return ""


def _build_query(
    *parts: str,
    clauses: list[tuple[str, list]] | None = None,
) -> tuple[str, list]:
    query_parts = list(parts)
    params: list = []
    if clauses:
        for clause, clause_params in clauses:
            if clause:
                query_parts.append(clause)
                params.extend(clause_params)
    return " ".join(query_parts), params


class ArticleSelector:
    def __init__(self, processed_db: ProcessedDatabase) -> None:
        self.processed_db = processed_db

    def _execute(self, query: str, params: list | None = None) -> sqlite3.Cursor:
        return self.processed_db.conn.execute(query, params or [])

    def get_article_details(self, processed_article_ids: list[int]) -> list[dict]:
        if not processed_article_ids:
            return []

        in_sub, in_params = _in_clause(processed_article_ids)
        query, params = _build_query(
            "SELECT a.*, p.*"
            " FROM articles a"
            " JOIN processed_articles p"
            "   ON a.id = p.fetched_article_id"
            " WHERE p.id IN",
            in_sub,
            clauses=[("", in_params)],
        )
        cursor = self._execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def _merge_details(
        self, rows: list[sqlite3.Row], details: list[dict]
    ) -> list[dict]:
        detail_map = {d["id"]: d for d in details}
        return [
            {
                **dict(row),
                **detail_map.get(row["fetched_article_id"], {}),
            }
            for row in rows
        ]

    def _select_featured_deals(
        self,
        current: str,
        upcoming: str,
    ) -> list[sqlite3.Row]:
        freshness = _freshness_clause("deal")

        query, params = _build_query(
            "SELECT * FROM processed_articles"
            " WHERE json_array_length(content_type) > 0"
            " AND json_extract(content_type, '$[0]') = 'deal'"
            " AND json_extract(deal_data, '$.value_score')"
            "   IS NOT NULL"
            " AND json_extract(deal_data, '$.booking_deadline')"
            "   IS NOT NULL"
            " AND date(json_extract("
            "   deal_data, '$.booking_deadline')) > date('now')",
            clauses=[
                freshness,
                (
                    "ORDER BY"
                    "   CASE"
                    "     WHEN json_extract("
                    "       seasonality, '$.' || ?) > 0 THEN 3"
                    "     WHEN json_extract("
                    "       seasonality, '$.' || ?) > 0 THEN 2"
                    "     ELSE 1"
                    "   END DESC,"
                    "   CAST(json_extract("
                    "     deal_data, '$.value_score')"
                    "     AS REAL) DESC,"
                    "   CASE"
                    "     WHEN date(json_extract("
                    "       deal_data, '$.booking_deadline'))"
                    "       < date('now', '+14 days') THEN 2"
                    "     WHEN date(json_extract("
                    "       deal_data, '$.booking_deadline'))"
                    "       < date('now', '+30 days') THEN 1"
                    "     ELSE 0"
                    "   END DESC"
                    " LIMIT 3",
                    [current, upcoming],
                ),
            ],
        )
        cursor = self._execute(query, params)
        deals = cursor.fetchall()

        if not deals:
            fallback = (
                "SELECT * FROM processed_articles"
                " WHERE json_array_length(content_type) > 0"
                " AND json_extract(content_type, '$[0]')"
                "   = 'deal'"
                " AND json_extract("
                "   deal_data, '$.booking_deadline')"
                "   IS NOT NULL"
                " AND date(json_extract("
                "   deal_data, '$.booking_deadline'))"
                "   > date('now')"
                " ORDER BY date(json_extract("
                "   deal_data, '$.booking_deadline')) ASC"
                " LIMIT 3"
            )
            cursor = self._execute(fallback)
            deals = cursor.fetchall()

        if not deals:
            msg = "No future deals found for newsletter"
            raise ValueError(msg)

        return deals

    def _select_location_guides(
        self,
        location: str,
        excluded_ids: list[int],
    ) -> list[sqlite3.Row]:
        if not location or location.lower() == "worldwide":
            return []

        freshness = _freshness_clause("guide")
        exclude = _exclude_ids_clause(excluded_ids)
        loc = location.lower()

        query, params = _build_query(
            "SELECT * FROM processed_articles"
            " WHERE json_array_length(content_type) > 0"
            " AND ("
            "   json_extract(content_type, '$[0]') = 'guide'"
            "   OR json_extract(content_type, '$[0]')"
            "     = 'experience'"
            " )",
            clauses=[
                freshness,
                exclude,
                (
                    "AND ("
                    "   json_extract(locations, '$.primary')"
                    "     = ?"
                    "   OR json_extract("
                    "     locations, '$.secondary') LIKE ?"
                    " )"
                    " ORDER BY"
                    "   json_extract(content_type, '$[0]')"
                    "     = 'guide' DESC,"
                    "   last_used IS NULL DESC,"
                    "   COALESCE(used_count, 0) ASC,"
                    "   processed_date DESC"
                    " LIMIT 2",
                    [loc, "%" + loc + "%"],
                ),
            ],
        )
        cursor = self._execute(query, params)
        return cursor.fetchall()

    def _select_more_deals(
        self,
        needed: int,
        excluded_ids: list[int],
    ) -> list[sqlite3.Row]:
        freshness = _freshness_clause("deal")
        exclude = _exclude_ids_clause(excluded_ids)

        query, params = _build_query(
            "SELECT * FROM processed_articles"
            " WHERE json_array_length(content_type) > 0"
            " AND json_extract(content_type, '$[0]') = 'deal'"
            " AND json_extract("
            "   deal_data, '$.booking_deadline') IS NOT NULL"
            " AND date(json_extract("
            "   deal_data, '$.booking_deadline'))"
            "   > date('now')",
            clauses=[
                exclude,
                freshness,
                (
                    "ORDER BY CAST(json_extract("
                    "   deal_data, '$.value_score')"
                    "   AS REAL) DESC"
                    " LIMIT ?",
                    [needed],
                ),
            ],
        )
        cursor = self._execute(query, params)
        return cursor.fetchall()

    def _select_by_type(
        self,
        content_type: str,
        excluded_ids: list[int],
        limit: int,
    ) -> list[sqlite3.Row]:
        freshness = _freshness_clause(content_type)
        exclude = _exclude_ids_clause(excluded_ids)

        query, params = _build_query(
            "SELECT * FROM processed_articles"
            " WHERE json_array_length(content_type) > 0"
            " AND json_extract(content_type, '$[0]') = ?",
            clauses=[
                ("", [content_type]),
                exclude,
                freshness,
                (
                    "ORDER BY"
                    "   last_used IS NULL DESC,"
                    "   COALESCE(used_count, 0) ASC,"
                    "   processed_date DESC"
                    " LIMIT ?",
                    [limit],
                ),
            ],
        )
        cursor = self._execute(query, params)
        return cursor.fetchall()

    def _select_seasonal_experience(
        self,
        excluded_ids: list[int],
        current: str,
        upcoming: str,
    ) -> sqlite3.Row | None:
        freshness = _freshness_clause("experience")
        exclude = _exclude_ids_clause(excluded_ids)

        query, params = _build_query(
            "SELECT * FROM processed_articles"
            " WHERE json_array_length(content_type) > 0"
            " AND json_extract(content_type, '$[0]')"
            "   = 'experience'",
            clauses=[
                exclude,
                freshness,
                (
                    "ORDER BY"
                    "   CASE"
                    "     WHEN json_extract("
                    "       seasonality, '$.' || ?)"
                    "       > 0 THEN 3"
                    "     WHEN json_extract("
                    "       seasonality, '$.' || ?)"
                    "       > 0 THEN 2"
                    "     ELSE 1"
                    "   END DESC,"
                    "   last_used IS NULL DESC,"
                    "   COALESCE(used_count, 0) ASC,"
                    "   processed_date DESC"
                    " LIMIT 1",
                    [current, upcoming],
                ),
            ],
        )
        cursor = self._execute(query, params)
        return cursor.fetchone()

    def _select_and_merge(
        self,
        content_type: str,
        selected_ids: list[int],
        limit: int,
    ) -> list[dict]:
        rows = self._select_by_type(content_type, selected_ids, limit=limit)
        if not rows:
            return []
        details = self.get_article_details([r["id"] for r in rows])
        selected_ids.extend(r["id"] for r in rows)
        return self._merge_details(rows, details)

    def _find_guides_for_deal(
        self,
        deal: sqlite3.Row,
        content: dict[str, Any],
        selected_ids: list[int],
    ) -> str:
        featured_loc = _extract_location(deal["locations"])
        deal_dest = self._extract_deal_destination(deal)

        for loc in [deal_dest, featured_loc]:
            if not loc or loc == "worldwide":
                continue
            guides = self._select_location_guides(loc, selected_ids)
            if not guides:
                continue
            guide_details = self.get_article_details([g["id"] for g in guides])
            content["featured_destination_guides"] = self._merge_details(
                guides, guide_details
            )
            selected_ids.extend(g["id"] for g in guides)
            guide_loc = _extract_location(guides[0]["locations"])
            if guide_loc and guide_loc != "worldwide":
                content["destination_focus"] = guide_loc
            break

        return featured_loc

    def select_newsletter_content(self) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        current = _current_season(now.month)
        upcoming = _next_season(current)

        content: dict[str, Any] = {}
        selected_ids: list[int] = []

        # 1. featured deals
        deals = self._select_featured_deals(current, upcoming)
        deal_details = self.get_article_details([d["id"] for d in deals])
        content["featured_deals"] = self._merge_details(deals, deal_details)
        selected_ids.extend(d["id"] for d in deals)

        # 2. location-relevant guides
        featured_loc = self._find_guides_for_deal(deals[0], content, selected_ids)

        # 3. more deals if needed
        if len(deals) < SEASONAL_CYCLE_WEEKS:
            needed = SEASONAL_CYCLE_WEEKS - len(deals)
            more = self._select_more_deals(needed, selected_ids)
            if more:
                more_details = self.get_article_details([d["id"] for d in more])
                content["featured_deals"].extend(
                    self._merge_details(more, more_details)
                )
                selected_ids.extend(d["id"] for d in more)

        # 4. travel news
        content["travel_news"] = self._select_and_merge("news", selected_ids, limit=3)

        # 5. practical tips
        content["practical_tips"] = self._select_and_merge("tip", selected_ids, limit=2)

        # 6. seasonal experience
        include_seasonal = now.isocalendar()[1] % SEASONAL_CYCLE_WEEKS == 0
        if include_seasonal:
            exp = self._select_seasonal_experience(selected_ids, current, upcoming)
            if exp:
                exp_details = self.get_article_details([exp["id"]])[0]
                content["seasonal_experience"] = {
                    **dict(exp),
                    **dict(exp_details),
                }
                selected_ids.append(exp["id"])

        # 7. metadata
        content["metadata"] = {
            "generation_date": now.isoformat(),
            "season": current,
            "upcoming_season": upcoming,
            "destination_focus": (
                featured_loc
                if featured_loc and featured_loc.lower() != "worldwide"
                else None
            ),
            "article_ids": selected_ids,
            "include_seasonal": include_seasonal,
        }

        return content

    @staticmethod
    def _extract_deal_destination(deal: sqlite3.Row) -> str:
        try:
            deal_data = (
                json.loads(deal["deal_data"])
                if isinstance(deal["deal_data"], str)
                else deal["deal_data"]
            )
            if deal_data and "destination" in deal_data:
                return deal_data["destination"].lower()
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        return ""
