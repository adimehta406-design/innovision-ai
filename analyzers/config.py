"""
Configuration for TruthLens AI Analyzers.
"""
import os

# OpenRouter Configuration
# OpenRouter Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Primary Brain (Claude 3.5 Sonnet)
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "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")
CLAUDE_MODEL = "anthropic/claude-3.5-sonnet"

# Secondary Brain (Gemini 2.0 Flash)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "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")
GEMINI_MODEL = "google/gemini-2.0-flash-001"

# Headers for OpenRouter (General)
def get_headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://truthlens.app",
        "X-Title": "TruthLens - Fake News Analyzer"
    }
