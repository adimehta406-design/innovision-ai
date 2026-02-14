"""
Universal Text Verifier
Verifies claims by cross-referencing with live web search results.
Combines DuckDuckGo Search, LLM-based claim extraction, and source credibility scoring.
Supports Multilingual Analysis and Fact-Check Database Integration.
"""

import logging
import json
import asyncio
import httpx
from urllib.parse import urlparse
from duckduckgo_search import DDGS
from . import config

logger = logging.getLogger(__name__)

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

FACT_CHECK_DOMAINS = [
    "snopes.com", "factcheck.org", "politifact.com", 
    "altnews.in", "boomlive.in", "vishvasnews.com"
]

SYSTEM_PROMPT_CLAIMS = """You are an expert fact-checker. Extract the core verifiable claims from the user's text.
The user may provide text in English, Hindi, or a mix (Hinglish).
If the text is in Hindi/Hinglish, translate the core claim to English for search, but keep the original nuance.

Return a JSON object with a key 'claims' containing a list of strings.
Each claim should be a standalone factual statement that can be verified via search.
Limit to the top 3 most important claims."""

SYSTEM_PROMPT_VERDICT = """You are TruthLens, an AI Verification Engine.
Analyze the provided search results to verify the user's claims.

Return a JSON object with:
1. "verdict": One of [TRUE, FALSE, MISLEADING, UNVERIFIED, OPINION]
2. "confidence": Integer 0-100
3. "truth_score": Integer 0-100 (0=False, 100=True)
4. "explanation": A concise 2-sentence summary of why the claim is true/false.
5. "missing_context": Any important context that is missing (optional).
6. "supporting_sources_count": Integer (How many sources support the claim?)
7. "opposing_sources_count": Integer (How many sources refute the claim?)

Base your verdict ONLY on the provided search context. If results are inconclusive, say UNVERIFIED."""


async def verify_text(text: str) -> dict:
    """
    Full Verification Pipeline:
    1. Extract Claims (LLM - Gemini 2.0 Flash)
    2. Search Web (DDG) - General & Fact-Check Specific
    3. Score Sources
    4. Generate Verdict (LLM - Claude 3.5 Sonnet)
    """
    result = {
        "text": text,
        "claims": [],
        "sources": [],
        "verdict": "UNVERIFIED",
        "truth_score": 0,
        "confidence": 0,
        "explanation": "Analysis pending...",
        "risk_level": "UNKNOWN",
        "supporting_sources_count": 0,
        "opposing_sources_count": 0
    }

    if not text or len(text.strip()) < 5:
        result["explanation"] = "Text too short to verify."
        return result

    try:
        # 1. Extract Claims (Use Gemini for speed)
        claims = await extract_claims_llm(text)
        result["claims"] = claims
        
        if not claims:
            result["explanation"] = "No verifiable claims found in text."
            return result
        
        main_claim = claims[0]

        # 2. Search Web - Parallel General Search & Fact-Check Search
        # We run them sequentially here for simplicity but could be parallel
        general_results = search_web(main_claim)
        fact_check_results = search_fact_checks(main_claim)
        
        # Combine and deduplicate based on URL
        all_results = fact_check_results + general_results
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r['href'] not in seen_urls:
                unique_results.append(r)
                seen_urls.add(r['href'])
        
        # 3. Analyze & Score Sources
        if unique_results:
            scored_sources = analyze_sources(unique_results)
            result["sources"] = scored_sources[:12] # Top 12
            
            # 4. Generate Verdict with Search Context (Use Claude for accuracy)
            verdict_data = await generate_verdict_llm(main_claim, scored_sources[:6])
            result.update(verdict_data)
        else:
            # Fallback to LLM Knowledge
            logger.warning("Web search failed. Falling back to LLM knowledge.")
            verdict_data = await verify_with_llm_knowledge(main_claim)
            result.update(verdict_data)
            result["explanation"] += " (Verified using AI Internal Knowledge)"
            result["sources"] = [{"domain": "ai-knowledge-base", "title": "AI Internal Knowledge based on Training Data", "body": "No external sources found.", "credibility_score": 70, "category": "AI Model"}]

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
            # Use Claude 3.5 Sonnet for Deep Knowledge
            response = await client.post(
                config.OPENROUTER_API_URL,
                headers=config.get_headers(config.CLAUDE_API_KEY),
                json={
                    "model": config.CLAUDE_MODEL,
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
    """Extract verifiable claims using LLM (Gemini)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Use Gemini 2.0 Flash for Speed
            response = await client.post(
                config.OPENROUTER_API_URL,
                headers=config.get_headers(config.GEMINI_API_KEY),
                json={
                    "model": config.GEMINI_MODEL,
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
            ddg_results = list(ddgs.text(query + " fact check", max_results=6))
            
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

def search_fact_checks(query: str) -> list:
    """Specific search targeting fact-checking databases."""
    results = []
    # Construct a query targeting known fact check sites
    sites = " OR ".join([f"site:{d}" for d in FACT_CHECK_DOMAINS])
    full_query = f"({sites}) {query}"
    
    try:
        with DDGS() as ddgs:
            ddg_results = list(ddgs.text(full_query, max_results=4))
            for r in ddg_results:
                results.append({
                    "title": "✅ " + r.get("title"), # Mark as fact check
                    "href": r.get("href"),
                    "body": r.get("body"),
                    "domain": urlparse(r.get("href", "")).netloc.replace("www.", "")
                })
    except Exception as e:
        logger.error(f"Fact check search failed: {e}")
    return results


def analyze_sources(results: list) -> list:
    """Score search results based on domain credibility."""
    scored = []
    for r in results:
        domain = r["domain"].lower()
        score = 50 # Neutral start
        category = "General Source"
        
        # Check Trust Lists
        if any(trusted in domain for trusted in TRUSTED_DOMAINS):
            score = 90
            category = "Trusted Source"
        elif any(q in domain for q in QUESTIONABLE_DOMAINS):
            score = 20
            category = "Questionable Source"
        elif "fact" in domain or "check" in domain or "news" in domain:
            score = 70
            category = "News/Fact-Check"
            
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
        context += f"Source {i+1} ({s['domain']}) [{s['category']}]: {s['title']} - {s['body']}\n"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Use Claude 3.5 Sonnet for Reasoning
            response = await client.post(
                config.OPENROUTER_API_URL,
                headers=config.get_headers(config.CLAUDE_API_KEY),
                json={
                    "model": config.CLAUDE_MODEL,
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
