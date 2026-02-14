"""
Configuration for TruthLens AI Analyzers.
"""
import os

# OpenRouter Configuration
# OpenRouter Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Primary Brain (Claude Opus 4.6)
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "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")
CLAUDE_MODEL = "anthropic/claude-opus-4.6"

# Secondary Brain (Components that previously used Gemini will now use Opus)
GEMINI_API_KEY = CLAUDE_API_KEY
GEMINI_MODEL = CLAUDE_MODEL

# Headers for OpenRouter (General)
def get_headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://truthlens.app",
        "X-Title": "TruthLens - Fake News Analyzer"
    }
