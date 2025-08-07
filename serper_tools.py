#!/usr/bin/env python3
"""
Enhanced Serper API integration for Wizzy Bot
Provides web search, news search, image search, and more
"""

import os
import requests
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Data class for search results"""
    title: str
    snippet: str
    link: str
    position: int = 0
    date: Optional[str] = None
    image_url: Optional[str] = None

@dataclass
class KnowledgeGraph:
    """Data class for knowledge graph results"""
    title: str
    type: str
    description: str
    attributes: Dict[str, Any]
    image_url: Optional[str] = None

class SerperAPI:
    """Enhanced Serper API client with multiple search types"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://google.serper.dev"
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        })
    
    def web_search(self, query: str, num_results: int = 5, country: str = "us") -> Dict[str, Any]:
        """Perform a web search"""
        return self._search(query, "search", num_results, country)
    
    def news_search(self, query: str, num_results: int = 5, country: str = "us") -> Dict[str, Any]:
        """Perform a news search"""
        return self._search(query, "news", num_results, country)
    
    def image_search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Perform an image search"""
        return self._search(query, "images", num_results)
    
    def video_search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Perform a video search"""
        return self._search(query, "videos", num_results)
    
    def shopping_search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Perform a shopping search"""
        return self._search(query, "shopping", num_results)
    
    def _search(self, query: str, search_type: str, num_results: int = 5, country: str = "us") -> Dict[str, Any]:
        """Internal method to perform different types of searches"""
        try:
            url = f"{self.base_url}/{search_type}"
            
            payload = {
                "q": query,
                "num": num_results
            }
            
            # Add country for web and news searches
            if search_type in ["search", "news"]:
                payload["gl"] = country
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            search_data = response.json()
            return self._process_search_response(search_data, query, search_type)
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error in {search_type} search: {e}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {self._get_error_message(response.status_code)}",
                "results": [],
                "search_type": search_type
            }
        except Exception as e:
            logger.error(f"Error in {search_type} search: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "search_type": search_type
            }
    
    def _process_search_response(self, data: Dict[str, Any], query: str, search_type: str) -> Dict[str, Any]:
        """Process and structure the search response"""
        results = []
        knowledge_graph = None
        
        # Process different result types based on search type
        if search_type == "search":
            results = self._process_organic_results(data.get("organic", []))
            knowledge_graph = self._process_knowledge_graph(data.get("knowledgeGraph"))
        elif search_type == "news":
            results = self._process_news_results(data.get("news", []))
        elif search_type == "images":
            results = self._process_image_results(data.get("images", []))
        elif search_type == "videos":
            results = self._process_video_results(data.get("videos", []))
        elif search_type == "shopping":
            results = self._process_shopping_results(data.get("shopping", []))
        
        return {
            "success": True,
            "query": query,
            "search_type": search_type,
            "results": results,
            "knowledge_graph": knowledge_graph,
            "total_results": len(results),
            "timestamp": datetime.now().isoformat()
        }
    
    def _process_organic_results(self, organic_data: List[Dict]) -> List[SearchResult]:
        """Process organic search results"""
        results = []
        for item in organic_data:
            results.append(SearchResult(
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                link=item.get("link", ""),
                position=item.get("position", 0),
                date=item.get("date")
            ))
        return results
    
    def _process_news_results(self, news_data: List[Dict]) -> List[SearchResult]:
        """Process news search results"""
        results = []
        for item in news_data:
            results.append(SearchResult(
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                link=item.get("link", ""),
                date=item.get("date"),
                image_url=item.get("imageUrl")
            ))
        return results
    
    def _process_image_results(self, image_data: List[Dict]) -> List[SearchResult]:
        """Process image search results"""
        results = []
        for item in image_data:
            results.append(SearchResult(
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                link=item.get("link", ""),
                image_url=item.get("imageUrl")
            ))
        return results
    
    def _process_video_results(self, video_data: List[Dict]) -> List[SearchResult]:
        """Process video search results"""
        results = []
        for item in video_data:
            results.append(SearchResult(
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                link=item.get("link", ""),
                image_url=item.get("imageUrl")
            ))
        return results
    
    def _process_shopping_results(self, shopping_data: List[Dict]) -> List[SearchResult]:
        """Process shopping search results"""
        results = []
        for item in shopping_data:
            results.append(SearchResult(
                title=item.get("title", ""),
                snippet=f"Price: {item.get('price', 'N/A')} - {item.get('snippet', '')}",
                link=item.get("link", ""),
                image_url=item.get("imageUrl")
            ))
        return results
    
    def _process_knowledge_graph(self, kg_data: Optional[Dict]) -> Optional[KnowledgeGraph]:
        """Process knowledge graph data"""
        if not kg_data:
            return None
        
        return KnowledgeGraph(
            title=kg_data.get("title", ""),
            type=kg_data.get("type", ""),
            description=kg_data.get("description", ""),
            attributes=kg_data.get("attributes", {}),
            image_url=kg_data.get("imageUrl")
        )
    
    def _get_error_message(self, status_code: int) -> str:
        """Get user-friendly error messages"""
        error_messages = {
            401: "Invalid API key. Please check your Serper API key.",
            403: "Access forbidden. Please check your API permissions.",
            429: "Rate limit exceeded. Please wait and try again.",
            500: "Serper API server error. Please try again later.",
            503: "Serper API service unavailable. Please try again later."
        }
        return error_messages.get(status_code, "Unknown error occurred")

class SearchFormatter:
    """Format search results for AI consumption"""
    
    @staticmethod
    def format_web_search(search_data: Dict[str, Any]) -> str:
        """Format web search results"""
        if not search_data["success"] or not search_data["results"]:
            return f"❌ Web search failed: {search_data.get('error', 'No results found')}"
        
        formatted = f"🌐 Web search results for: '{search_data['query']}'\n\n"
        
        # Add knowledge graph
        if search_data.get("knowledge_graph"):
            kg = search_data["knowledge_graph"]
            formatted += f"💡 **{kg.title}** ({kg.type})\n"
            formatted += f"   {kg.description}\n\n"
        
        # Add search results
        for i, result in enumerate(search_data["results"], 1):
            formatted += f"{i}. **{result.title}**\n"
            formatted += f"   {result.snippet}\n"
            formatted += f"   🔗 {result.link}\n\n"
        
        return formatted
    
    @staticmethod
    def format_news_search(search_data: Dict[str, Any]) -> str:
        """Format news search results"""
        if not search_data["success"] or not search_data["results"]:
            return f"❌ News search failed: {search_data.get('error', 'No results found')}"
        
        formatted = f"📰 News results for: '{search_data['query']}'\n\n"
        
        for i, result in enumerate(search_data["results"], 1):
            formatted += f"{i}. **{result.title}**\n"
            formatted += f"   {result.snippet}\n"
            if result.date:
                formatted += f"   📅 {result.date}\n"
            formatted += f"   🔗 {result.link}\n\n"
        
        return formatted
    
    @staticmethod
    def format_for_ai_context(search_data: Dict[str, Any]) -> str:
        """Format search results as context for AI"""
        if not search_data["success"] or not search_data["results"]:
            return "No relevant search results found."
        
        context = f"Search results for '{search_data['query']}':\n\n"
        
        # Add knowledge graph first
        if search_data.get("knowledge_graph"):
            kg = search_data["knowledge_graph"]
            context += f"Key Information: {kg.title} ({kg.type})\n"
            context += f"{kg.description}\n\n"
        
        # Add top results
        for result in search_data["results"][:5]:  # Limit to top 5 for context
            context += f"- {result.title}\n"
            context += f"  {result.snippet}\n"
            if hasattr(result, 'date') and result.date:
                context += f"  Date: {result.date}\n"
            context += f"  Source: {result.link}\n\n"
        
        return context

# Utility functions for easy integration
def quick_web_search(query: str, api_key: str, num_results: int = 5) -> Dict[str, Any]:
    """Quick web search function"""
    serper = SerperAPI(api_key)
    return serper.web_search(query, num_results)

def quick_news_search(query: str, api_key: str, num_results: int = 5) -> Dict[str, Any]:
    """Quick news search function"""
    serper = SerperAPI(api_key)
    return serper.news_search(query, num_results)
