import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

MAX_RESULTS = 5
MAX_CONTENT_CHARS = 500

_api_key = os.environ.get("TAVILY_API_KEY")
_client = TavilyClient(api_key=_api_key) if _api_key else None


def search_web(query: str = "") -> str:
    """Search the web and return cleaned, relevant content.

    query defaults to empty rather than being required, because the
    local model sometimes calls tools with no arguments — returning a
    readable error it can recover from beats crashing.
    """
    query = query.strip()
    if not query:
        return "Error: no search query given."

    if _client is None:
        return (
            "Error: TAVILY_API_KEY not found. Add it to a .env file in the "
            "project root (see .env.example)."
        )

    try:
        response = _client.search(
            query=query,
            max_results=MAX_RESULTS,
            include_answer=True,  # Tavily's own summarised answer, when it has one
        )
    except Exception as e:
        return f"Error searching the web: {e}"

    parts = []

    # Tavily often returns a direct answer synthesised from the sources.
    # Putting it first gives a weak model the answer without needing to
    # extract it from the raw results itself.
    answer = response.get("answer")
    if answer:
        parts.append(f"Summary: {answer}")

    results = response.get("results", [])
    if not results and not answer:
        return f"No results found for '{query}'."

    for i, result in enumerate(results, start=1):
        title = result.get("title", "(no title)")
        content = result.get("content", "")
        url = result.get("url", "")
        if len(content) > MAX_CONTENT_CHARS:
            content = content[:MAX_CONTENT_CHARS] + "…"
        parts.append(f"{i}. {title}\n{content}\nSource: {url}")

    return "\n\n".join(parts)


SEARCH_WEB_SCHEMA = {
    "name": "search_web",
    "description": (
        "Search the web for current information. Use this for anything you "
        "don't already know or that may have changed recently: news, sports "
        "results, prices, documentation, current events, or facts about the "
        "world outside the user's computer. Base your answer only on what the "
        "results actually say — if they don't answer the question, say so "
        "rather than guessing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query, phrased as you'd type it into a search engine.",
            }
        },
        "required": ["query"],
    },
}