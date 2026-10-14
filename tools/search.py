from ddgs import DDGS
import trafilatura

def search_web(query: str, max_results: int = 5, timelimit: str = None) -> str:
    """
    Searches DuckDuckGo for live internet links and snippets.
    
    Args:
        query: The search query string. Can include site filters like 'site:linkedin.com/jobs'.
        max_results: Number of results to return (default 5).
        timelimit: Optional time filter: 'd' (past day), 'w' (past week), 'm' (past month), 'y' (past year).
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Searching the web for '{query}' (timelimit: {timelimit})...")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, timelimit=timelimit))
            
        if not results:
            return f"No results found on the web for '{query}'."
            
        formatted = [f"Search Results for '{query}':\n"]
        for idx, res in enumerate(results):
            formatted.append(
                f"{idx + 1}. Title: {res.get('title', 'No Title')}\n"
                f"   URL: {res.get('href', 'No URL')}\n"
                f"   Snippet: {res.get('body', 'No Snippet')}\n"
            )
        return "\n".join(formatted)
        
    except Exception as e:
        return f"Search failed: {e}"

def fetch_webpage_content(url: str) -> str:
    """
    Downloads and extracts the full readable text content from a given webpage URL.
    Use this after searching when you need to read the full article, documentation, or page details.
    
    Args:
        url: The exact URL of the webpage to read.
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Reading full webpage content from -> {url}...")
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return f"Failed to download webpage content from {url}."
            
        # Extract main body text and strip navigation/ads
        text_content = trafilatura.extract(downloaded)
        
        if not text_content:
            return f"Could not extract readable text from {url}."
            
        # Limit content length to avoid overwhelming the model context
        max_chars = 8000
        truncated_text = text_content[:max_chars]
        
        if len(text_content) > max_chars:
            truncated_text += "\n\n[Content truncated for length]..."
            
        return f"Full Webpage Content ({url}):\n\n{truncated_text}"
        
    except Exception as e:
        return f"Failed to read webpage: {e}"