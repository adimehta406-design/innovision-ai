<p align="center">
  <h1 align="center">🔍 TruthLens</h1>
  <p align="center"><strong>Fake News Visual Analyzer</strong></p>
  <p align="center">AI-powered forensic analysis to detect manipulated images, fake screenshots, and AI-generated content.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109-green?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/OpenCV-4.9-red?logo=opencv" alt="OpenCV">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
  <img src="https://img.shields.io/badge/Status-Hackathon%20Ready-brightgreen" alt="Status">
</p>

---

## 🎯 Problem

Visual misinformation is one of the most dangerous forms of fake news. Doctored images, misleading screenshots, and AI-generated content spread faster than text — causing real-world harm including communal violence, election interference, and health scares.

**TruthLens** gives journalists, fact-checkers, and citizens a one-click forensic analysis tool.

## ✨ Features

| Engine | What It Does |
|--------|-------------|
| 📋 **EXIF Analysis** | Extract metadata — detect editing software, stripped data, date tampering |
| 🔥 **Error Level Analysis** | Detect image splicing via JPEG compression inconsistency heatmaps |
| 🔎 **Tamper Detection** | Copy-move forgery (ORB), edge anomalies, noise inconsistency analysis |
| 📝 **OCR Analysis** | Extract text from screenshots, detect misinformation language patterns |
| 🤖 **AI Detection** | Frequency domain + texture + color entropy analysis for AI-generated images |
| ⚖️ **AI Verdict** | LLM-powered contextual verdict with actionable recommendations |

## 🏗️ Architecture

```
Frontend (HTML/CSS/JS) → FastAPI Backend → Analysis Pipeline
                                          ├─ EXIF Analyzer
                                          ├─ ELA Analyzer
                                          ├─ Tamper Detector (OpenCV)
                                          ├─ OCR Analyzer
                                          ├─ AI Detector
                                          ├─ Risk Scorer (weighted)
                                          └─ AI Verdict (OpenRouter API)
```

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/your-username/truthlens.git
cd truthlens

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

Open **http://localhost:8000** in your browser.

## 📁 Project Structure

```
truthlens/
├── main.py                  # FastAPI app & API routes
├── requirements.txt         # Python dependencies
├── analyzers/
│   ├── __init__.py
│   ├── exif_analyzer.py     # EXIF metadata extraction
│   ├── ela_analyzer.py      # Error Level Analysis
│   ├── tamper_detector.py   # OpenCV tampering detection
│   ├── ocr_analyzer.py      # OCR + misinformation patterns
│   ├── ai_detector.py       # AI-generated image detection
│   ├── risk_scorer.py       # Weighted risk scoring engine
│   └── verdict_generator.py # OpenRouter AI verdict
├── static/
│   ├── index.html           # Frontend SPA
│   ├── style.css            # Premium dark theme
│   └── app.js               # Frontend logic
└── README.md
```

## 🧮 Risk Scoring

| Analyzer | Weight | Criteria |
|----------|--------|----------|
| EXIF | 20% | Missing/stripped metadata, editing software |
| ELA | 25% | Compression inconsistencies, hotspot % |
| Tampering | 25% | Copy-move matches, noise variance |
| OCR | 15% | Urgency words, clickbait, misinformation patterns |
| AI Detection | 15% | Frequency, texture, color entropy |

**Thresholds**: 0-25 LOW • 26-50 MEDIUM • 51-75 HIGH • 76-100 CRITICAL

## 🛠️ Tech Stack

- **Backend**: Python 3.9+, FastAPI, Uvicorn
- **Computer Vision**: OpenCV, Pillow, NumPy
- **AI**: OpenRouter API (Gemini Flash)
- **Frontend**: Vanilla HTML/CSS/JS (no framework needed)
- **Design**: Dark theme, glassmorphism, canvas gauges

## ⚠️ Limitations

- OCR works best with English text (Tesseract optional for better accuracy)
- AI detection uses statistical heuristics, not a trained ML model
- Reverse image search requires external API integration
- Designed as a screening tool — not a definitive forensic system

## 🔮 Future Scope

- Train custom CNN for manipulation detection
- Integrate Google Vision / TinEye for reverse image search
- Multi-language OCR support
- Browser extension for real-time social media checking
- Mobile app (React Native)
- Fact-check database integration (IFCN, AltNews, BoomLive)

## 📄 License

MIT License — Built for truth. Open source forever.
