"""
Web search tool definition for NEXUS.

Provides web search functionality using the Tavily API. This module defines
the web_search function and its corresponding tool metadata for LLM integration.
"""

import os
import logging
from typing import Dict, Any, Union, List
from tavily import TavilyClient

logger = logging.getLogger(__name__)

# Constants
MAX_SEARCH_RESULTS = 5
CONTENT_PREVIEW_LENGTH = 200
DEFAULT_TITLE = "No title"
DEFAULT_URL = "No URL"
DEFAULT_CONTENT = "No content available"
ENV_VAR_API_KEY = "TAVILY_API_KEY"


def _format_search_results(query: str, response: Dict[str, Any], include_answer: bool = False) -> str:
    """
    Format search results into a readable string.

    Args:
        query: The original search query
        response: The response from Tavily API
        include_answer: Whether to include AI-generated answer summary

    Returns:
        Formatted search results string
    """
    if not response or "results" not in response:
        return f"No search results found for query: {query}"

    results = response["results"]
    if not results:
        return f"No search results found for query: {query}"

    # Start with AI answer if requested and available
    formatted_results = ""
    if include_answer and "answer" in response and response["answer"]:
        formatted_results += f"**AI Summary:**\n{response['answer']}\n\n"

    # Format the search results
    formatted_results += f"**Search results for '{query}':**\n\n"

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


def web_search(query: str, max_results: int = 5, include_answer: bool = False) -> str:
    """
    Perform a web search using the Tavily API.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (0-20, default: 5)
        include_answer: Whether to include AI-generated answer summary (default: False)

    Returns:
        A formatted string containing search results and optionally AI answer

    Raises:
        ValueError: If TAVILY_API_KEY environment variable is not set or max_results is invalid
        Exception: If the search request fails
    """
    # Validate max_results
    if not 0 <= max_results <= 20:
        raise ValueError("max_results must be between 0 and 20")

    logger.info(f"Executing web search for query: {query}, max_results: {max_results}, include_answer: {include_answer}")

    # Get API key from environment
    api_key = os.getenv(ENV_VAR_API_KEY)
    if not api_key:
        error_msg = f"{ENV_VAR_API_KEY} environment variable not set"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        # Initialize Tavily client
        client = TavilyClient(api_key=api_key)

        # Perform search with max_results parameter
        response = client.search(query, max_results=max_results)

        # Format results
        formatted_results = _format_search_results(query, response, include_answer)
        logger.info(f"Web search completed successfully for query: {query}")
        return formatted_results

    except Exception as e:
        error_msg = f"Web search failed for query '{query}': {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def web_extract(urls: Union[str, List[str]]) -> str:
    """
    Extract raw content from web pages using the Tavily Extract API.

    Args:
        urls: A single URL string or list of URLs to extract content from

    Returns:
        A formatted string containing extracted raw content from the URLs

    Raises:
        ValueError: If TAVILY_API_KEY environment variable is not set
        Exception: If the extraction request fails
    """
    logger.info(f"Executing web extract for URLs: {urls}")

    # Get API key from environment
    api_key = os.getenv(ENV_VAR_API_KEY)
    if not api_key:
        error_msg = f"{ENV_VAR_API_KEY} environment variable not set"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Convert single URL to list
    if isinstance(urls, str):
        urls_list = [urls]
    else:
        urls_list = urls

    try:
        # Initialize Tavily client
        client = TavilyClient(api_key=api_key)

        # Perform extraction
        response = client.extract(urls_list, extract_depth="basic", include_images=False)

        # Format results
        formatted_results = _format_extract_results(urls_list, response)
        logger.info(f"Web extract completed successfully for URLs: {urls}")
        return formatted_results

    except Exception as e:
        error_msg = f"Web extract failed for URLs {urls}: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def _format_extract_results(urls: List[str], response: Dict[str, Any]) -> str:
    """
    Format extraction results into a readable string.

    Args:
        urls: The original URLs that were extracted
        response: The response from Tavily Extract API

    Returns:
        Formatted extraction results string
    """
    if not response:
        return f"No extraction results found for URLs: {urls}"

    formatted_results = ""

    # Process successful results
    if "results" in response and response["results"]:
        for result in response["results"]:
            url = result.get("url", "Unknown URL")
            raw_content = result.get("raw_content", "No content available")

            formatted_results += f"**Extracted content from {url}:**\n"
            formatted_results += f"{raw_content}\n\n"

    # Process failed results
    if "failed_results" in response and response["failed_results"]:
        formatted_results += "**Failed extractions:**\n"
        for failed in response["failed_results"]:
            url = failed.get("url", "Unknown URL")
            error = failed.get("error", "Unknown error")
            formatted_results += f"- Failed to extract: {url} (Error: {error})\n"
        formatted_results += "\n"

    # If no results at all
    if not formatted_results.strip():
        return f"No content could be extracted from URLs: {urls}"

    return formatted_results.strip()


# Tool definition in OpenAI/Google format for LLM integration
WEB_SEARCH_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information on any topic. Returns formatted search results with titles, URLs, and content snippets. Supports max_results (0-20) to control result count and include_answer to get AI-generated summaries.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find information about"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of search results to return (0-20, default: 5)",
                    "default": 5
                },
                "include_answer": {
                    "type": "boolean",
                    "description": "Whether to include AI-generated answer summary (default: False)",
                    "default": False
                }
            },
            "required": ["query"]
        }
    }
}

WEB_EXTRACT_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "web_extract",
        "description": "Extract raw content from web pages. Returns the full text content from specified URLs for detailed analysis.",
        "parameters": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "string",
                    "description": "A single URL or comma-separated list of URLs to extract content from"
                }
            },
            "required": ["urls"]
        }
    }
}