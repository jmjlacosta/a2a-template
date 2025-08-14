#!/usr/bin/env python3
"""
Document Analyzer Agent - Intelligent document analysis with chunking.

This example demonstrates:
- Document chunking and segmentation
- Keyword extraction
- Summary generation using LLM
- Combining LLM with deterministic processing
- Tool-based document operations

Usage:
    export GOOGLE_API_KEY="your-key"  # or OPENAI_API_KEY or ANTHROPIC_API_KEY
    python document_analyzer_agent.py

The agent can:
- Split documents into semantic chunks
- Extract keywords and key phrases
- Generate summaries
- Identify document structure
- Extract key information
"""

import os
import sys
import re
import json
import uvicorn
from typing import List, Dict, Any
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from google.adk import get_llm
from google.adk.tools import FunctionTool
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class DocumentAnalyzerAgent(A2AAgent):
    """Analyze documents with intelligent processing."""
    
    def __init__(self):
        super().__init__()
        self._llm = None
        self._tools = None
        self._initialize_tools()
    
    def get_agent_name(self) -> str:
        return "Document Analyzer"
    
    def get_agent_description(self) -> str:
        return "Analyzes documents with chunking, keyword extraction, and summarization"
    
    def _initialize_tools(self):
        """Initialize document analysis tools."""
        self._tools = [
            FunctionTool(self._extract_chunks),
            FunctionTool(self._find_keywords),
            FunctionTool(self._analyze_structure),
            FunctionTool(self._extract_entities)
        ]
    
    async def process_message(self, message: str) -> str:
        """Process document analysis request using LLM with tools."""
        # Initialize LLM if needed
        if self._llm is None:
            system_instruction = """You are a document analysis expert specialized in:
        
1. Document Structure Analysis
   - Identify sections, headers, and paragraphs
   - Detect document type (report, article, memo, etc.)
   
2. Information Extraction
   - Extract key facts and figures
   - Identify main topics and themes
   - Find action items and conclusions
   
3. Summarization
   - Create concise summaries
   - Highlight important points
   - Preserve critical information

Use the available tools to process documents effectively.
Be precise and thorough in your analysis."""
            
            self._llm = get_llm(system_instruction=system_instruction)
        
        # Generate response with tools
        response = self._llm.generate_text(
            prompt=message,
            tools=self._tools
        )
        
        return response
    
    def _extract_chunks(self, text: str, chunk_size: int = 500) -> str:
        """Split text into semantic chunks.
        
        Args:
            text: The document text to chunk
            chunk_size: Target size for each chunk in characters
            
        Returns:
            JSON array of text chunks with metadata
        """
        # Split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            # If paragraph itself is too long, split by sentences
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) < chunk_size:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk:
                            chunks.append({
                                "index": chunk_index,
                                "text": current_chunk.strip(),
                                "length": len(current_chunk.strip())
                            })
                            chunk_index += 1
                        current_chunk = sentence + " "
            else:
                # Add paragraph to current chunk
                if len(current_chunk) + len(para) < chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append({
                            "index": chunk_index,
                            "text": current_chunk.strip(),
                            "length": len(current_chunk.strip())
                        })
                        chunk_index += 1
                    current_chunk = para + "\n\n"
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                "index": chunk_index,
                "text": current_chunk.strip(),
                "length": len(current_chunk.strip())
            })
        
        return json.dumps({
            "total_chunks": len(chunks),
            "average_chunk_size": sum(c["length"] for c in chunks) // len(chunks) if chunks else 0,
            "chunks": chunks
        }, indent=2)
    
    def _find_keywords(self, text: str, max_keywords: int = 15) -> str:
        """Extract keywords from text.
        
        Args:
            text: The document text to analyze
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            JSON object with extracted keywords and frequencies
        """
        # Simple keyword extraction (production would use NLP libraries)
        # Remove common words and extract significant terms
        
        common_words = {
            "the", "is", "at", "which", "on", "a", "an", "as", "are", 
            "was", "were", "been", "be", "have", "has", "had", "do", 
            "does", "did", "will", "would", "could", "should", "may",
            "might", "must", "can", "could", "this", "that", "these",
            "those", "i", "you", "he", "she", "it", "we", "they", "to",
            "of", "in", "for", "with", "by", "from", "about", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "under", "again", "further", "then", "once"
        }
        
        # Extract words
        words = re.findall(r'\b[a-z]+\b', text.lower())
        
        # Count frequencies
        word_freq = {}
        for word in words:
            if len(word) > 3 and word not in common_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:max_keywords]
        
        return json.dumps({
            "keywords": [{"word": word, "frequency": freq} for word, freq in keywords],
            "total_unique_words": len(word_freq),
            "total_words": len(words)
        }, indent=2)
    
    def _analyze_structure(self, text: str) -> str:
        """Analyze document structure.
        
        Args:
            text: The document text to analyze
            
        Returns:
            JSON object with structural analysis
        """
        lines = text.split('\n')
        
        structure = {
            "total_lines": len(lines),
            "total_paragraphs": len([p for p in text.split('\n\n') if p.strip()]),
            "total_sentences": len(re.findall(r'[.!?]+', text)),
            "total_words": len(text.split()),
            "total_characters": len(text),
            "sections": []
        }
        
        # Detect potential headers (lines that are short and possibly titles)
        for i, line in enumerate(lines):
            if line.strip() and len(line) < 100:
                # Check if it might be a header
                if (line.isupper() or 
                    line[0].isupper() and not line.endswith('.') or
                    re.match(r'^\d+\.?\s+\w+', line)):
                    structure["sections"].append({
                        "line": i + 1,
                        "text": line.strip(),
                        "type": "potential_header"
                    })
        
        # Detect lists
        list_items = re.findall(r'^[\s]*[-•*]\s+.+$', text, re.MULTILINE)
        numbered_items = re.findall(r'^[\s]*\d+\.\s+.+$', text, re.MULTILINE)
        
        structure["lists"] = {
            "bullet_points": len(list_items),
            "numbered_items": len(numbered_items)
        }
        
        return json.dumps(structure, indent=2)
    
    def _extract_entities(self, text: str) -> str:
        """Extract named entities from text.
        
        Args:
            text: The document text to analyze
            
        Returns:
            JSON object with extracted entities
        """
        entities = {
            "dates": [],
            "numbers": [],
            "emails": [],
            "urls": [],
            "capitalized_phrases": []
        }
        
        # Extract dates (simple patterns)
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'
        ]
        for pattern in date_patterns:
            entities["dates"].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Extract numbers with context
        number_matches = re.finditer(r'\b\d+(?:\.\d+)?(?:%|km|m|kg|lb|USD|EUR|GBP)?\b', text)
        for match in number_matches:
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context = text[start:end].strip()
            entities["numbers"].append({
                "value": match.group(),
                "context": context
            })
        
        # Extract emails
        entities["emails"] = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        
        # Extract URLs
        entities["urls"] = re.findall(r'https?://[^\s]+', text)
        
        # Extract capitalized phrases (potential names/organizations)
        cap_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
        entities["capitalized_phrases"] = list(set(cap_phrases))[:10]
        
        return json.dumps(entities, indent=2)


# Module-level app creation for HealthUniverse deployment
agent = DocumentAnalyzerAgent()
agent_card = agent.create_agent_card()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

# Create the app - for HealthUniverse deployment
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8003))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)