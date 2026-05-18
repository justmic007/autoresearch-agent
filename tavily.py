# Tavily search tool with retry logic
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import TAVILY_API_KEY

_client = TavilyClient(api_key=TAVILY_API_KEY)


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=6))
def search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web for a query.
    Returns a list of {title, url, content} dicts.
    """
    response = _client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
    )
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        }
        for r in response.get("results", [])
    ]
