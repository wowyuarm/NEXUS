"""
Unit tests for web_search tool.

These tests verify that the web_search function correctly handles search operations,
result formatting, and error handling. All external dependencies are mocked
to ensure isolation.
"""

import os
from unittest.mock import Mock

import pytest

from nexus.tools.definition.web import (
    WEB_EXTRACT_TOOL,
    WEB_SEARCH_TOOL,
    _format_search_results,
    web_extract,
    web_search,
)


class TestWebSearchTool:
    """Test suite for web_search tool functionality."""

    def test_format_search_results_with_valid_data(self):
        """Test formatting of valid search results."""
        query = "python programming"
        response = {
            "results": [
                {
                    "title": "Python Tutorial",
                    "url": "https://example.com/python-tutorial",
                    "content": "This is a comprehensive Python programming tutorial that covers all the basics.",
                },
                {
                    "title": "Advanced Python",
                    "url": "https://example.com/advanced-python",
                    "content": "Learn advanced Python concepts and best practices for professional development.",
                },
            ]
        }

        result = _format_search_results(query, response, include_answer=False)

        assert "Search results for 'python programming':" in result
        assert "1. **Python Tutorial**" in result
        assert "URL: https://example.com/python-tutorial" in result
        assert "Content: This is a comprehensive Python programming tutorial" in result
        assert "2. **Advanced Python**" in result
        assert "URL: https://example.com/advanced-python" in result
        assert "Content: Learn advanced Python concepts" in result

    def test_format_search_results_content_truncation(self):
        """Test that long content is properly truncated."""
        query = "test query"
        # Create content longer than 200 characters
        long_content = "A" * 250  # 250 characters
        response = {
            "results": [
                {
                    "title": "Long Content",
                    "url": "https://example.com/long",
                    "content": long_content,
                }
            ]
        }

        result = _format_search_results(query, response, include_answer=False)

        # Check that content is truncated with ellipsis
        assert "Content: " + "A" * 200 + "..." in result

    def test_format_search_results_with_empty_results(self):
        """Test formatting when API returns no results."""
        query = "nonexistent query"
        response = {"results": []}

        result = _format_search_results(query, response, include_answer=False)

        assert result == f"No search results found for query: {query}"

    def test_format_search_results_with_missing_results_key(self):
        """Test formatting when response doesn't have results key."""
        query = "test query"
        response = {"error": "API error"}

        result = _format_search_results(query, response, include_answer=False)

        assert result == f"No search results found for query: {query}"

    def test_format_search_results_with_none_response(self):
        """Test formatting when response is None."""
        query = "test query"
        response = None

        result = _format_search_results(query, response, include_answer=False)

        assert result == f"No search results found for query: {query}"

    def test_format_search_results_with_default_values(self):
        """Test formatting with missing optional fields."""
        query = "test query"
        response = {
            "results": [
                {
                    # Missing title, url, and content
                }
            ]
        }

        result = _format_search_results(query, response, include_answer=False)

        assert "1. **No title**" in result
        assert "URL: No URL" in result
        assert "Content: No content available" in result

    def test_format_search_results_respects_max_results(self):
        """Test that only the maximum number of results is formatted."""
        query = "test query"
        # Create more results than MAX_SEARCH_RESULTS (5)
        results = []
        for i in range(10):
            results.append(
                {
                    "title": f"Result {i+1}",
                    "url": f"https://example.com/result{i+1}",
                    "content": f"Content for result {i+1}",
                }
            )

        response = {"results": results}

        result = _format_search_results(query, response, include_answer=False)

        # Should only have 5 results (1-5), not all 10
        for i in range(1, 6):
            assert f"{i}. **Result {i}**" in result

        # Should not have results 6-10
        for i in range(6, 11):
            assert f"{i}. **Result {i}**" not in result

    def test_web_search_raises_error_if_api_key_missing(self, monkeypatch):
        """Test that web_search raises ValueError when API key is missing."""
        # Remove the environment variable
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)

        with pytest.raises(
            ValueError, match="TAVILY_API_KEY environment variable not set"
        ):
            web_search("test query")

    def test_web_search_success_with_api_key(self, monkeypatch, mocker):
        """Test successful web search with valid API key."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient
        mock_client = Mock()
        mock_response = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com/test",
                    "content": "Test content",
                }
            ]
        }
        mock_client.search.return_value = mock_response

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        result = web_search("test query")

        # Verify the client was initialized with correct API key
        mock_tavily_client_class.assert_called_once_with(api_key="test_api_key")

        # Verify search was called with correct query and default max_results
        mock_client.search.assert_called_once_with("test query", max_results=5)

        # Verify result is properly formatted
        assert "Search results for 'test query':" in result
        assert "Test Result" in result

    def test_web_search_api_error_handling(self, monkeypatch, mocker):
        """Test that web_search handles API errors correctly."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient to raise an exception
        mock_client = Mock()
        mock_client.search.side_effect = Exception("API Error: Rate limit exceeded")

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        with pytest.raises(
            Exception,
            match="Web search failed for query 'test query': API Error: Rate limit exceeded",
        ):
            web_search("test query")

    def test_web_search_tool_definition_structure(self):
        """Test that the tool definition has the correct structure."""
        assert WEB_SEARCH_TOOL["type"] == "function"
        assert "function" in WEB_SEARCH_TOOL
        assert WEB_SEARCH_TOOL["function"]["name"] == "web_search"
        assert "description" in WEB_SEARCH_TOOL["function"]
        assert "parameters" in WEB_SEARCH_TOOL["function"]
        assert WEB_SEARCH_TOOL["function"]["parameters"]["type"] == "object"
        assert "properties" in WEB_SEARCH_TOOL["function"]["parameters"]
        assert "required" in WEB_SEARCH_TOOL["function"]["parameters"]
        assert "query" in WEB_SEARCH_TOOL["function"]["parameters"]["required"]
        assert "query" in WEB_SEARCH_TOOL["function"]["parameters"]["properties"]
        assert (
            WEB_SEARCH_TOOL["function"]["parameters"]["properties"]["query"]["type"]
            == "string"
        )

    def test_web_search_with_complex_results(self):
        """Test formatting of complex search results with special characters."""
        query = "Python & AI"
        response = {
            "results": [
                {
                    "title": "Python & Artificial Intelligence: A Complete Guide",
                    "url": "https://example.com/python-ai",
                    "content": "This comprehensive guide covers the intersection of Python programming and artificial intelligence, including machine learning, deep learning, and neural networks. Perfect for developers looking to expand their skills.",
                },
                {
                    "title": "Special Characters: Test",
                    "url": "https://example.com/special-chars",
                    "content": "Testing special characters like @#$%^&*() in search results. Also testing quotes: 'single' and \"double\".",
                },
            ]
        }

        result = _format_search_results(query, response, include_answer=False)

        assert "Search results for 'Python & AI':" in result
        assert "Python & Artificial Intelligence: A Complete Guide" in result
        assert "Special Characters: Test" in result
        assert "Testing special characters like @#$%^&*()" in result

    def test_web_search_unicode_handling(self):
        """Test that the function handles Unicode content properly."""
        query = "测试查询"
        response = {
            "results": [
                {
                    "title": "测试标题",
                    "url": "https://example.com/test",
                    "content": "这是一个包含中文内容的测试结果。也包含 emoji: 🚀",
                }
            ]
        }

        result = _format_search_results(query, response, include_answer=False)

        assert "Search results for '测试查询':" in result
        assert "测试标题" in result
        assert "这是一个包含中文内容的测试结果" in result
        assert "🚀" in result

    def test_web_search_empty_content_handling(self):
        """Test handling of results with empty or whitespace-only content."""
        query = "test query"
        response = {
            "results": [
                {
                    "title": "Empty Content",
                    "url": "https://example.com/empty",
                    "content": "",
                },
                {
                    "title": "Whitespace Content",
                    "url": "https://example.com/whitespace",
                    "content": "   \n\t  ",
                },
                {
                    "title": "Normal Content",
                    "url": "https://example.com/normal",
                    "content": "Normal content here",
                },
            ]
        }

        result = _format_search_results(query, response, include_answer=False)

        # All content should be processed normally
        assert "Empty Content" in result
        assert "Whitespace Content" in result
        assert "Normal Content" in result

    @pytest.mark.parametrize("api_key_value", [None, ""])
    def test_web_search_various_missing_api_key_scenarios(
        self, monkeypatch, api_key_value
    ):
        """Test various scenarios where API key is missing or invalid."""
        if api_key_value is None:
            monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        else:
            monkeypatch.setenv("TAVILY_API_KEY", api_key_value)

        with pytest.raises(
            ValueError, match="TAVILY_API_KEY environment variable not set"
        ):
            web_search("test query")

    def test_web_search_monkeypatch_environment_variable(self, mocker):
        """Test using monkeypatch to temporarily set environment variable."""
        # Mock the environment variable using monkeypatch
        mocker.patch.dict(os.environ, {"TAVILY_API_KEY": "monkeypatch_test_key"})

        # Mock TavilyClient
        mock_client = Mock()
        mock_response = {
            "results": [
                {
                    "title": "Monkeypatch Test",
                    "url": "https://example.com/test",
                    "content": "Testing monkeypatch functionality",
                }
            ]
        }
        mock_client.search.return_value = mock_response

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        result = web_search("monkeypatch test")

        # Verify the client was initialized with the mocked API key
        mock_tavily_client_class.assert_called_once_with(api_key="monkeypatch_test_key")
        assert "Monkeypatch Test" in result


class TestWebExtractTool:
    """Test suite for web_extract tool functionality."""

    def test_web_extract_raises_error_if_api_key_missing(self, monkeypatch):
        """Test that web_extract raises ValueError when API key is missing."""
        # Remove the environment variable
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)

        with pytest.raises(
            ValueError, match="TAVILY_API_KEY environment variable not set"
        ):
            web_extract("https://example.com")

    def test_web_extract_success_with_api_key(self, monkeypatch, mocker):
        """Test successful web extract with valid API key."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient
        mock_client = Mock()
        mock_response = {
            "results": [
                {
                    "url": "https://example.com/test",
                    "raw_content": "This is the extracted raw content from the webpage.",
                    "images": [],
                    "favicon": "https://example.com/favicon.ico",
                }
            ],
            "failed_results": [],
            "response_time": 0.5,
        }
        mock_client.extract.return_value = mock_response

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        result = web_extract("https://example.com")

        # Verify the client was initialized with correct API key
        mock_tavily_client_class.assert_called_once_with(api_key="test_api_key")

        # Verify extract was called with correct URL
        mock_client.extract.assert_called_once_with(
            ["https://example.com"], extract_depth="basic", include_images=False
        )

        # Verify result contains extracted content
        assert "Extracted content from https://example.com/test:" in result
        assert "This is the extracted raw content from the webpage." in result

    def test_web_extract_with_multiple_urls(self, monkeypatch, mocker):
        """Test web extract with multiple URLs."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient
        mock_client = Mock()
        mock_response = {
            "results": [
                {
                    "url": "https://example.com/page1",
                    "raw_content": "Content from page 1",
                    "images": [],
                    "favicon": "https://example.com/favicon.ico",
                },
                {
                    "url": "https://example.com/page2",
                    "raw_content": "Content from page 2",
                    "images": [],
                    "favicon": "https://example.com/favicon.ico",
                },
            ],
            "failed_results": [],
            "response_time": 0.8,
        }
        mock_client.extract.return_value = mock_response

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        result = web_extract(["https://example.com/page1", "https://example.com/page2"])

        # Verify extract was called with correct URLs
        mock_client.extract.assert_called_once_with(
            ["https://example.com/page1", "https://example.com/page2"],
            extract_depth="basic",
            include_images=False,
        )

        # Verify result contains content from both pages
        assert "Content from page 1" in result
        assert "Content from page 2" in result

    def test_web_extract_api_error_handling(self, monkeypatch, mocker):
        """Test that web_extract handles API errors correctly."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient to raise an exception
        mock_client = Mock()
        mock_client.extract.side_effect = Exception("API Error: Invalid URL")

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        with pytest.raises(
            Exception, match="Web extract failed for URLs.*API Error: Invalid URL"
        ):
            web_extract("https://invalid-url.com")

    def test_web_extract_with_failed_results(self, monkeypatch, mocker):
        """Test web extract when some URLs fail to extract."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient
        mock_client = Mock()
        mock_response = {
            "results": [
                {
                    "url": "https://example.com/success",
                    "raw_content": "Successfully extracted content",
                    "images": [],
                    "favicon": "https://example.com/favicon.ico",
                }
            ],
            "failed_results": [
                {
                    "url": "https://example.com/failed",
                    "error": "Unable to extract content",
                }
            ],
            "response_time": 0.6,
        }
        mock_client.extract.return_value = mock_response

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        result = web_extract(
            ["https://example.com/success", "https://example.com/failed"]
        )

        # Verify result contains successful content
        assert "Successfully extracted content" in result
        # Verify result mentions failed extraction
        assert "Failed to extract: https://example.com/failed" in result

    def test_web_extract_tool_definition_structure(self):
        """Test that the web_extract tool definition has the correct structure."""
        assert WEB_EXTRACT_TOOL["type"] == "function"
        assert "function" in WEB_EXTRACT_TOOL
        assert WEB_EXTRACT_TOOL["function"]["name"] == "web_extract"
        assert "description" in WEB_EXTRACT_TOOL["function"]
        assert "parameters" in WEB_EXTRACT_TOOL["function"]
        assert WEB_EXTRACT_TOOL["function"]["parameters"]["type"] == "object"
        assert "properties" in WEB_EXTRACT_TOOL["function"]["parameters"]
        assert "required" in WEB_EXTRACT_TOOL["function"]["parameters"]
        assert "urls" in WEB_EXTRACT_TOOL["function"]["parameters"]["required"]
        assert "urls" in WEB_EXTRACT_TOOL["function"]["parameters"]["properties"]
        assert (
            WEB_EXTRACT_TOOL["function"]["parameters"]["properties"]["urls"]["type"]
            == "string"
        )


class TestEnhancedWebSearchTool:
    """Test suite for enhanced web_search tool with new parameters."""

    def test_web_search_with_max_results(self, monkeypatch, mocker):
        """Test web_search with max_results parameter."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient
        mock_client = Mock()
        mock_response = {
            "results": [
                {
                    "title": f"Result {i}",
                    "url": f"https://example.com/result{i}",
                    "content": f"Content {i}",
                }
                for i in range(3)  # Only return 3 results even though we ask for more
            ]
        }
        mock_client.search.return_value = mock_response

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        result = web_search("test query", max_results=10)

        # Verify search was called with max_results parameter
        mock_client.search.assert_called_once_with("test query", max_results=10)

    def test_web_search_with_include_answer_true(self, monkeypatch, mocker):
        """Test web_search with include_answer=True."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient
        mock_client = Mock()
        mock_response = {
            "answer": "This is the AI-generated answer summary.",
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com/test",
                    "content": "Test content",
                }
            ],
        }
        mock_client.search.return_value = mock_response

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        result = web_search("test query", include_answer=True)

        # Verify search was called correctly with default max_results
        mock_client.search.assert_called_once_with("test query", max_results=5)

        # Verify result includes the AI answer
        assert "AI Summary:" in result
        assert "This is the AI-generated answer summary." in result

    def test_web_search_with_include_answer_false(self, monkeypatch, mocker):
        """Test web_search with include_answer=False."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient
        mock_client = Mock()
        mock_response = {
            "answer": "This should not be included.",
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com/test",
                    "content": "Test content",
                }
            ],
        }
        mock_client.search.return_value = mock_response

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        result = web_search("test query", include_answer=False)

        # Verify result does not include the AI answer
        assert "AI Summary:" not in result
        assert "This should not be included." not in result

    def test_web_search_with_no_answer_in_response(self, monkeypatch, mocker):
        """Test web_search when API response doesn't include answer field."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient
        mock_client = Mock()
        mock_response = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com/test",
                    "content": "Test content",
                }
            ]
            # No "answer" field
        }
        mock_client.search.return_value = mock_response

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        result = web_search("test query", include_answer=True)

        # Verify result handles missing answer gracefully
        assert "Search results for 'test query':" in result
        assert "Test Result" in result

    def test_web_search_with_both_new_parameters(self, monkeypatch, mocker):
        """Test web_search with both max_results and include_answer parameters."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient
        mock_client = Mock()
        mock_response = {
            "answer": "AI-generated summary.",
            "results": [
                {
                    "title": "Result 1",
                    "url": "https://example.com/1",
                    "content": "Content 1",
                },
                {
                    "title": "Result 2",
                    "url": "https://example.com/2",
                    "content": "Content 2",
                },
            ],
        }
        mock_client.search.return_value = mock_response

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        result = web_search("test query", max_results=5, include_answer=True)

        # Verify search was called with max_results parameter
        mock_client.search.assert_called_once_with("test query", max_results=5)

        # Verify result includes both answer and results
        assert "AI Summary:" in result
        assert "AI-generated summary." in result
        assert "Result 1" in result
        assert "Result 2" in result

    def test_web_search_max_results_validation(self, monkeypatch, mocker):
        """Test web_search max_results parameter validation."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )

        # Test max_results too low
        with pytest.raises(ValueError, match="max_results must be between 0 and 20"):
            web_search("test query", max_results=-1)

        # Test max_results too high
        with pytest.raises(ValueError, match="max_results must be between 0 and 20"):
            web_search("test query", max_results=21)

    def test_web_search_default_values(self, monkeypatch, mocker):
        """Test web_search with default parameter values."""
        # Set the environment variable
        monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")

        # Mock TavilyClient
        mock_client = Mock()
        mock_response = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com/test",
                    "content": "Test content",
                }
            ]
        }
        mock_client.search.return_value = mock_response

        mock_tavily_client_class = mocker.patch(
            "nexus.tools.definition.web.TavilyClient"
        )
        mock_tavily_client_class.return_value = mock_client

        # Call with only required parameter
        result = web_search("test query")

        # Verify search was called with default max_results (5)
        mock_client.search.assert_called_once_with("test query", max_results=5)
