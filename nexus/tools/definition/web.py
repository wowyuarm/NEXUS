"""
Web search tool definition for NEXUS.

Provides web search functionality using the Tavily API. This module defines
the web_search function and its corresponding tool metadata for LLM integration.
"""

import os
import logging
from typing import Dict, Any
from tavily import TavilyClient

logger = logging.getLogger(__name__)

# Constants
MAX_SEARCH_RESULTS = 5
CONTENT_PREVIEW_LENGTH = 200
DEFAULT_TITLE = "No title"
DEFAULT_URL = "No URL"
DEFAULT_CONTENT = "No content available"
ENV_VAR_API_KEY = "TAVILY_API_KEY"


def _format_search_results(query: str, response: Dict[str, Any]) -> str:
    """
    Format search results into a readable string.

    Args:
        query: The original search query
        response: The response from Tavily API

    Returns:
        Formatted search results string
    """
    if not response or "results" not in response:
        return f"No search results found for query: {query}"

    results = response["results"]
    if not results:
        return f"No search results found for query: {query}"

    # Format the top results into a readable string
    formatted_results = f"Search results for '{query}':\n\n"

    for i, result in enumerate(results[:MAX_SEARCH_RESULTS], 1):
        title = result.get("title", DEFAULT_TITLE)
        url = result.get("url", DEFAULT_URL)
        content = result.get("content", DEFAULT_CONTENT)

        formatted_results += f"{i}. **{title}**\n"
        formatted_results += f"   URL: {url}\n"
        content_preview = content[:CONTENT_PREVIEW_LENGTH]
        if len(content) > CONTENT_PREVIEW_LENGTH:
            content_preview += "..."
        formatted_results += f"   Content: {content_preview}\n\n"

    return formatted_results


def web_search(query: str) -> str:
    """
    Perform a web search using the Tavily API.

    Args:
        query: The search query string

    Returns:
        A formatted string containing search results

    Raises:
        ValueError: If TAVILY_API_KEY environment variable is not set
        Exception: If the search request fails
    """
    logger.info(f"Executing web search for query: {query}")

    # Get API key from environment
    api_key = os.getenv(ENV_VAR_API_KEY)
    if not api_key:
        error_msg = f"{ENV_VAR_API_KEY} environment variable not set"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        # Initialize Tavily client
        client = TavilyClient(api_key=api_key)

        # Perform search
        response = client.search(query)

        # Format results
        formatted_results = _format_search_results(query, response)
        logger.info(f"Web search completed successfully for query: {query}")
        return formatted_results

    except Exception as e:
        error_msg = f"Web search failed for query '{query}': {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


# Tool definition in OpenAI/Google format for LLM integration
WEB_SEARCH_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information on any topic. Returns formatted search results with titles, URLs, and content snippets.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find information about"
                }
            },
            "required": ["query"]
        }
    }
}