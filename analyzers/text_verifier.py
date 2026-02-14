"""
Universal Text Verifier
Verifies claims by cross-referencing with live web search results.
Combines DuckDuckGo Search, LLM-based claim extraction, and source credibility scoring.
"""

import logging
import json
import asyncio
import httpx
from urllib.parse import urlparse
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = "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"

# Source Credibility Lists (Hackathon Scale)
TRUSTED_DOMAINS = {
    # International Wire/News
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "npr.org", "pbs.org",
    "bloomberg.com", "nytimes.com", "washingtonpost.com", "wsj.com",
    "theguardian.com", "aljazeera.com", "dw.com", "france24.com",

    # Fact Checkers
    "snopes.com", "factcheck.org", "politifact.com", "fullfact.org",
    "altnews.in", "boomlive.in", "thequint.com", "newschecker.in",
    "vishvasnews.com", "indiatoday.in", "check4spam.com",

    # India Specific
    "ndtv.com", "thehindu.com", "indianexpress.com", "livemint.com",
    "timesofindia.indiatimes.com", "scroll.in", "thewire.in", "newslaundry.com",
    "ptinews.com", "aniin.com",

    # Science/Health
    "who.int", "cdc.gov", "nih.gov", "mayoclinic.org", "nature.com",
    "science.org", "nasa.gov", "un.org"
}

QUESTIONABLE_DOMAINS = {
    "onion.com", "infowars.com", "breitbart.com", "sputniknews.com",
    "rt.com", "globaltimes.cn", "dailymail.co.uk", "thesun.co.uk", 
    "nypost.com", "opindia.com", "postcard.news"
}

SYSTEM_PROMPT_CLAIMS = """You are an expert fact-checker. Extract the core verifiable claims from the user's text.
Return a JSON object with a key 'claims' containing a list of strings.
Each claim should be a standalone factual statement that can be verified via search.
Limit to the top 3 most important claims.
If the text is just a query, return it as the single claim."""

SYSTEM_PROMPT_VERDICT = """You are TruthLens, an AI Verification Engine.
Analyze the provided search results to verify the user's claims.

Return a JSON object with:
1. "verdict": One of [TRUE, FALSE, MISLEADING, UNVERIFIED, OPINION]
2. "confidence": Integer 0-100
3. "truth_score": Integer 0-100 (0=False, 100=True)
4. "explanation": A concise 2-sentence summary of why the claim is true/false.
5. "missing_context": Any important context that is missing (optional).

Base your verdict ONLY on the provided search context. If results are inconclusive, say UNVERIFIED."""


async def verify_text(text: str) -> dict:
    """
    Full Verification Pipeline:
    1. Extract Claims (LLM)
    2. Search Web (DDG)
    3. Score Sources
    4. Generate Verdict (LLM)
    """
    result = {
        "text": text,
        "claims": [],
        "sources": [],
        "verdict": "UNVERIFIED",
        "truth_score": 0,
        "confidence": 0,
        "explanation": "Analysis pending...",
        "risk_level": "UNKNOWN"
    }

    if not text or len(text.strip()) < 5:
        result["explanation"] = "Text too short to verify."
        return result

    try:
        # 1. Extract Claims
        claims = await extract_claims_llm(text)
        result["claims"] = claims
        
        if not claims:
            result["explanation"] = "No verifiable claims found in text."
            return result


        # 2. Search Web
        search_results = search_web(claims[0])
        
        # 3. Analyze & Score Sources
        if search_results:
            scored_sources = analyze_sources(search_results)
            result["sources"] = scored_sources[:10] # Top 10
            
            # 4. Generate Verdict with Search Context
            verdict_data = await generate_verdict_llm(claims[0], scored_sources[:5])
            result.update(verdict_data)
        else:
            # Fallback to LLM Knowledge
            logger.warning("Web search failed. Falling back to LLM knowledge.")
            verdict_data = await verify_with_llm_knowledge(claims[0])
            result.update(verdict_data)
            result["explanation"] += " (Verified using AI Internal Knowledge)"
            result["sources"] = [{"domain": "ai-knowledge-base", "title": "AI Internal Knowledge", "body": "Verification based on model training data.", "credibility_score": 70, "category": "AI Model"}]

        # Calculate Risk Level based on Truth Score
        score = result["truth_score"]
        if score < 30:
            result["risk_level"] = "CRITICAL" # False
        elif score < 60:
            result["risk_level"] = "HIGH" # Misleading/Mixed
        elif score < 80:
            result["risk_level"] = "MEDIUM" # Unverified/Opinion
        else:
            result["risk_level"] = "LOW" # True

    except Exception as e:
        logger.error(f"Text verification failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        result["explanation"] = f"An error occurred during verification: {str(e)}"

    return result


async def verify_with_llm_knowledge(claim: str) -> dict:
    """Verify claim using LLM internal knowledge if search fails."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-2.0-flash-001",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT_VERDICT},
                        {"role": "user", "content": f"Claim: {claim}\n\nNo external search results available. Verify this based on your internal knowledge training data. Be conservative."}
                    ],
                    "response_format": { "type": "json_object" }
                }
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            # Cap confidence for internal knowledge
            result["confidence"] = min(result.get("confidence", 0), 80)
            return result
    except Exception as e:
        logger.error(f"LLM fallback failed: {e}")
        return {
            "verdict": "UNVERIFIED",
            "truth_score": 50,
            "confidence": 0,
            "explanation": "Could not verify claim due to lack of information."
        }



async def extract_claims_llm(text: str) -> list:
    """Extract verifiable claims using LLM."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-2.0-flash-001",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT_CLAIMS},
                        {"role": "user", "content": text}
                    ],
                    "response_format": { "type": "json_object" }
                }
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return parsed.get("claims", [text])
    except Exception as e:
        logger.warning(f"Claim extraction failed: {e}")
        return [text] # Fallback to using full text as claim


def search_web(query: str) -> list:
    """Search DuckDuckGo for the query."""
    results = []
    try:
        with DDGS() as ddgs:
            # Use 'news' backend for fresher results, or 'text' for general
            # For verification, 'text' is often better for fact checks
            ddg_results = list(ddgs.text(query + " fact check", max_results=8))
            
            for r in ddg_results:
                results.append({
                    "title": r.get("title"),
                    "href": r.get("href"),
                    "body": r.get("body"),
                    "domain": urlparse(r.get("href", "")).netloc.replace("www.", "")
                })
    except Exception as e:
        logger.error(f"Search failed: {e}")
    return results


def analyze_sources(results: list) -> list:
    """Score search results based on domain credibility."""
    scored = []
    for r in results:
        domain = r["domain"].lower()
        score = 50 # Neutral start
        category = "Unknown"
        
        # Check Trust Lists
        if any(trusted in domain for trusted in TRUSTED_DOMAINS):
            score = 90
            category = "Trusted Source"
        elif any(q in domain for q in QUESTIONABLE_DOMAINS):
            score = 20
            category = "Questionable Source"
            
        r["credibility_score"] = score
        r["category"] = category
        scored.append(r)
        
    # Sort by credibility
    scored.sort(key=lambda x: x["credibility_score"], reverse=True)
    return scored


async def generate_verdict_llm(claim: str, sources: list) -> dict:
    """Generate final verdict using LLM based on search results."""
    
    # Prepare context from search snippets
    context = ""
    for i, s in enumerate(sources):
        context += f"Source {i+1} ({s['domain']}): {s['title']} - {s['body']}\n"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-2.0-flash-001",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT_VERDICT},
                        {"role": "user", "content": f"Claim: {claim}\n\nSearch Context:\n{context}"}
                    ],
                    "response_format": { "type": "json_object" }
                }
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
            
    except Exception as e:
        logger.error(f"Verdict generation failed: {e}")
        return {
            "verdict": "UNVERIFIED",
            "truth_score": 50,
            "confidence": 0,
            "explanation": "Could not generate AI verdict due to connection error."
        }
