import os
import re
from typing import List, Dict, Any

class LocalRetriever:
    def __init__(self, kb_dir: str = "knowledge_base"):
        """
        Initializes the retriever with the directory of text files.
        """
        # Resolve path relative to project root or workspace
        self.kb_dir = os.path.abspath(kb_dir)
        self.documents = []
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """
        Loads all .txt files from the knowledge base directory
        and splits them into paragraphs/sections.
        """
        if not os.path.exists(self.kb_dir):
            print(f"Warning: Knowledge base directory '{self.kb_dir}' not found.")
            return

        for filename in os.listdir(self.kb_dir):
            if filename.endswith(".txt"):
                file_path = os.path.join(self.kb_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                        # Split by double newlines to get individual sections/paragraphs
                        sections = content.split("\n\n")
                        for idx, section in enumerate(sections):
                            section = section.strip()
                            if section:
                                self.documents.append({
                                    "source": filename,
                                    "section_id": idx,
                                    "content": section,
                                    # Store a clean set of words for keyword matching
                                    "words": set(re.findall(r"\w+", section.lower()))
                                })
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        
        print(f"Loaded {len(self.documents)} text sections from knowledge base.")

    def retrieve(self, query: str, category: str = None, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Retrieves the top_k most relevant documents from the knowledge base.
        Filters by category keyword if provided, then scores based on term overlap.
        """
        if not self.documents:
            return []

        # Tokenize and clean the query
        query_words = set(re.findall(r"\w+", query.lower()))
        if not query_words:
            return self.documents[:top_k]

        scored_docs = []
        for doc in self.documents:
            # Calculate word intersection (overlap)
            matching_words = doc["words"].intersection(query_words)
            score = len(matching_words)
            
            # Boost score if category matches the document content/filename
            # E.g., if category is "refunds", boost files containing "refund" or "return"
            if category:
                cat_lower = category.lower()
                source_lower = doc["source"].lower()
                if cat_lower in source_lower or any(cat_lower in w for w in doc["words"]):
                    score += 3.0  # Give a significant boost to matching category files
            
            # Additional small boost if source matches keywords in query
            # E.g., if query contains "shipping", boost shipping_info.txt
            for word in query_words:
                if word in doc["source"].lower():
                    score += 2.0

            if score > 0:
                scored_docs.append({
                    "content": doc["content"],
                    "source": doc["source"],
                    "score": score
                })

        # Sort documents by score descending
        scored_docs.sort(key=lambda x: x["score"], reverse=True)

        # Fallback to top_k default documents if no matches found
        if not scored_docs:
            return [{
                "content": doc["content"],
                "source": doc["source"],
                "score": 0.0
            } for doc in self.documents[:top_k]]

        return scored_docs[:top_k]

# Simple test code
if __name__ == "__main__":
    retriever = LocalRetriever("knowledge_base")
    results = retriever.retrieve("how long does a refund take?", category="Refunds & Returns")
    for r in results:
        print(f"Source: {r['source']} (Score: {r['score']})")
        print(r['content'])
        print("-" * 40)
