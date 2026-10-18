import re
from typing import Any

from fastapi import FastAPI
from fastapi import HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pymongo import DESCENDING
from pymongo.errors import PyMongoError
from pathlib import Path
from fastapi.staticfiles import StaticFiles

from database import connect_to_database, get_collections


app = FastAPI(title="Daily Global Tech News API")
STATIC_DIRECTORY = Path(__file__).with_name("static")
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")


@app.get("/")
def read_root() -> FileResponse:
    """Serve the technology news dashboard."""
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/health")
def health_check() -> JSONResponse:
    """Check whether MongoDB can be reached."""
    client = None
    try:
        client, _ = connect_to_database()
    except ConnectionError:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "unavailable"},
        )
    finally:
        if client is not None:
            client.close()

    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "database": "available"},
    )


@app.get("/api/news")
def get_news(
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    category: str | None = Query(default=None, min_length=1, max_length=50),
) -> list[dict[str, Any]]:
    """Return saved news articles with optional search and category filters."""
    client = None
    try:
        client, database = connect_to_database()
        news_collection, _ = get_collections(database)

        filters: dict[str, Any] = {}
        if category and category.strip():
            filters["category"] = category.strip()

        search_text = search.strip() if search else ""
        if search_text:
            escaped_search = re.escape(search_text)
            filters["$or"] = [
                {"title": {"$regex": escaped_search, "$options": "i"}},
                {"description": {"$regex": escaped_search, "$options": "i"}},
                {"source": {"$regex": escaped_search, "$options": "i"}},
            ]

        articles = list(
            news_collection.find(filters)
            .sort("collected_at", DESCENDING)
            .limit(limit)
        )
        for article in articles:
            article["_id"] = str(article["_id"])
        return articles
    except ConnectionError as error:
        raise HTTPException(
            status_code=503,
            detail="MongoDB is currently unavailable.",
        ) from error
    except PyMongoError as error:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve news from MongoDB.",
        ) from error
    finally:
        if client is not None:
            client.close()
