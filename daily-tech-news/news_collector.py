import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

import requests
from dotenv import load_dotenv
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from database import connect_to_database, get_collections


load_dotenv(Path(__file__).with_name(".env"))

GNEWS_API_URL = os.getenv(
    "GNEWS_API_URL",
    "https://gnews.io/api/v4/search",
)
GNEWS_API_KEY_ENV = "GNEWS_API_KEY"
REQUEST_TIMEOUT_SECONDS = 15

CATEGORY_QUERIES = {
    "AI": '"artificial intelligence" OR AI',
    "Python": "Python AND (programming OR software)",
    "Cloud Computing": '"cloud computing" OR AWS OR Azure OR "Google Cloud"',
    "Cybersecurity": '"cybersecurity" OR "information security"',
    "Technology Companies": (
        '"technology companies" OR Apple OR Google OR Microsoft OR Nvidia'
    ),
}

logger = logging.getLogger(__name__)


def get_api_key() -> str:
    """Read the GNews API key from the environment or .env file."""
    api_key = os.getenv(GNEWS_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(
            f"Set the {GNEWS_API_KEY_ENV} environment variable or add it to .env."
        )
    return api_key


def fetch_news(query: str, api_key: str) -> list[dict[str, Any]]:
    """Fetch one category of articles using GNews's search endpoint."""
    try:
        response = requests.get(
            GNEWS_API_URL,
            params={
                "q": query,
                "lang": "en",
                "max": 10,
                "sortby": "publishedAt",
            },
            headers={"X-Api-Key": api_key},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"GNews request failed: {error}") from error

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError("GNews returned a response that was not valid JSON.") from error

    if not isinstance(data, dict):
        raise RuntimeError("GNews returned an unexpected response format.")

    articles = data.get("articles")
    if not isinstance(articles, list):
        raise RuntimeError("GNews response is missing its articles list.")
    return articles


def save_article(
    collection: Collection,
    article: Mapping[str, Any],
    category: str,
) -> Optional[bool]:
    """Save an article once, using its URL to identify duplicates."""
    title = article.get("title")
    url = article.get("url")
    if not isinstance(title, str) or not title.strip():
        logger.warning("Skipping an article in %s because its title is missing.", category)
        return None
    if not isinstance(url, str) or not url.strip():
        logger.warning("Skipping article %r because its URL is missing.", title)
        return None

    source_info = article.get("source")
    source = source_info.get("name") if isinstance(source_info, dict) else None

    document = {
        "title": title,
        "description": article.get("description"),
        "url": url,
        "source": source,
        "publication_date": article.get("publishedAt"),
        "category": category,
        "collected_at": datetime.now(timezone.utc),
    }

    try:
        result = collection.update_one(
            {"url": url},
            {"$setOnInsert": document},
            upsert=True,
        )
    except DuplicateKeyError:
        return False
    return result.upserted_id is not None


def collect_news() -> dict[str, int]:
    """Fetch the configured categories and store new articles in MongoDB."""
    api_key = get_api_key()
    client, database = connect_to_database()
    news_collection, _ = get_collections(database)
    counts = {"inserted": 0, "duplicates": 0, "skipped": 0}

    try:
        news_collection.create_index("url", unique=True)
        for category, query in CATEGORY_QUERIES.items():
            articles = fetch_news(query, api_key)
            for article in articles:
                if not isinstance(article, dict):
                    logger.warning(
                        "Skipping a malformed article returned for %s.",
                        category,
                    )
                    counts["skipped"] += 1
                else:
                    saved = save_article(news_collection, article, category)
                    if saved is True:
                        counts["inserted"] += 1
                    elif saved is False:
                        counts["duplicates"] += 1
                    else:
                        counts["skipped"] += 1
    except PyMongoError as error:
        raise RuntimeError(f"MongoDB error while collecting news: {error}") from error
    finally:
        client.close()

    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(collect_news())
