from ddgs import DDGS

MAX_RESULTS = 5
MAX_SNIPPET_CHARS = 300


def search_web(query: str) -> str:
    """Search the web and return the top results as readable text."""
    query = query.strip()
    if not query:
        return "Error: no search query given."

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=MAX_RESULTS))
    except Exception as e:
        return f"Error searching the web: {e}"

    if not results:
        return f"No results found for '{query}'."

    lines = []
    for i, result in enumerate(results, start=1):
        title = result.get("title", "(no title)")
        body = result.get("body", "")
        url = result.get("href", "")
        if len(body) > MAX_SNIPPET_CHARS:
            body = body[:MAX_SNIPPET_CHARS] + "…"
        lines.append(f"{i}. {title}\n{body}\nSource: {url}")

    return "\n\n".join(lines)


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