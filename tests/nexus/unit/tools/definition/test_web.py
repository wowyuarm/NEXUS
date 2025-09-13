"""
Unit tests for web_search tool.

These tests verify that the web_search function correctly handles search operations,
result formatting, and error handling. All external dependencies are mocked
to ensure isolation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import os

from nexus.tools.definition.web import web_search, _format_search_results, WEB_SEARCH_TOOL


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
                    "content": "This is a comprehensive Python programming tutorial that covers all the basics."
                },
                {
                    "title": "Advanced Python",
                    "url": "https://example.com/advanced-python",
                    "content": "Learn advanced Python concepts and best practices for professional development."
                }
            ]
        }
        
        result = _format_search_results(query, response)
        
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
                    "content": long_content
                }
            ]
        }
        
        result = _format_search_results(query, response)
        
        # Check that content is truncated with ellipsis
        assert "Content: " + "A" * 200 + "..." in result

    def test_format_search_results_with_empty_results(self):
        """Test formatting when API returns no results."""
        query = "nonexistent query"
        response = {
            "results": []
        }
        
        result = _format_search_results(query, response)
        
        assert result == f"No search results found for query: {query}"

    def test_format_search_results_with_missing_results_key(self):
        """Test formatting when response doesn't have results key."""
        query = "test query"
        response = {
            "error": "API error"
        }
        
        result = _format_search_results(query, response)
        
        assert result == f"No search results found for query: {query}"

    def test_format_search_results_with_none_response(self):
        """Test formatting when response is None."""
        query = "test query"
        response = None
        
        result = _format_search_results(query, response)
        
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
        
        result = _format_search_results(query, response)
        
        assert "1. **No title**" in result
        assert "URL: No URL" in result
        assert "Content: No content available" in result

    def test_format_search_results_respects_max_results(self):
        """Test that only the maximum number of results is formatted."""
        query = "test query"
        # Create more results than MAX_SEARCH_RESULTS (5)
        results = []
        for i in range(10):
            results.append({
                "title": f"Result {i+1}",
                "url": f"https://example.com/result{i+1}",
                "content": f"Content for result {i+1}"
            })
        
        response = {"results": results}
        
        result = _format_search_results(query, response)
        
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
        
        with pytest.raises(ValueError, match="TAVILY_API_KEY environment variable not set"):
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
                    "content": "Test content"
                }
            ]
        }
        mock_client.search.return_value = mock_response
        
        mock_tavily_client_class = mocker.patch('nexus.tools.definition.web.TavilyClient')
        mock_tavily_client_class.return_value = mock_client
        
        result = web_search("test query")
        
        # Verify the client was initialized with correct API key
        mock_tavily_client_class.assert_called_once_with(api_key="test_api_key")
        
        # Verify search was called with correct query
        mock_client.search.assert_called_once_with("test query")
        
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
        
        mock_tavily_client_class = mocker.patch('nexus.tools.definition.web.TavilyClient')
        mock_tavily_client_class.return_value = mock_client
        
        with pytest.raises(Exception, match="Web search failed for query 'test query': API Error: Rate limit exceeded"):
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
        assert WEB_SEARCH_TOOL["function"]["parameters"]["properties"]["query"]["type"] == "string"

    def test_web_search_with_complex_results(self):
        """Test formatting of complex search results with special characters."""
        query = "Python & AI"
        response = {
            "results": [
                {
                    "title": "Python & Artificial Intelligence: A Complete Guide",
                    "url": "https://example.com/python-ai",
                    "content": "This comprehensive guide covers the intersection of Python programming and artificial intelligence, including machine learning, deep learning, and neural networks. Perfect for developers looking to expand their skills."
                },
                {
                    "title": "Special Characters: Test",
                    "url": "https://example.com/special-chars",
                    "content": "Testing special characters like @#$%^&*() in search results. Also testing quotes: 'single' and \"double\"."
                }
            ]
        }
        
        result = _format_search_results(query, response)
        
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
                    "content": "这是一个包含中文内容的测试结果。也包含 emoji: 🚀"
                }
            ]
        }
        
        result = _format_search_results(query, response)
        
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
                    "content": ""
                },
                {
                    "title": "Whitespace Content", 
                    "url": "https://example.com/whitespace",
                    "content": "   \n\t  "
                },
                {
                    "title": "Normal Content",
                    "url": "https://example.com/normal",
                    "content": "Normal content here"
                }
            ]
        }
        
        result = _format_search_results(query, response)
        
        # All content should be processed normally
        assert "Empty Content" in result
        assert "Whitespace Content" in result
        assert "Normal Content" in result

    @pytest.mark.parametrize("api_key_value", [
        None,
        ""
    ])
    def test_web_search_various_missing_api_key_scenarios(self, monkeypatch, api_key_value):
        """Test various scenarios where API key is missing or invalid."""
        if api_key_value is None:
            monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        else:
            monkeypatch.setenv("TAVILY_API_KEY", api_key_value)
        
        with pytest.raises(ValueError, match="TAVILY_API_KEY environment variable not set"):
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
                    "content": "Testing monkeypatch functionality"
                }
            ]
        }
        mock_client.search.return_value = mock_response
        
        mock_tavily_client_class = mocker.patch('nexus.tools.definition.web.TavilyClient')
        mock_tavily_client_class.return_value = mock_client
        
        result = web_search("monkeypatch test")
        
        # Verify the client was initialized with the mocked API key
        mock_tavily_client_class.assert_called_once_with(api_key="monkeypatch_test_key")
        assert "Monkeypatch Test" in result