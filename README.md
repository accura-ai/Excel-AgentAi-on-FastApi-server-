# 🗂️ ExcelAgentAI
 
> **Local AI agent for Excel automation — your data stays on your machine, always.**
 
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![LangGraph](https://img.shields.io/badge/LangGraph-latest-blueviolet?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688?style=flat-square)
![Ollama](https://img.shields.io/badge/Ollama-Qwen3_14B-orange?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
 
---
 
## 🔒 Why this exists
 
Most AI tools for Excel send your entire file to a remote server. That means your private data — salary sheets, client lists, confidential reports — leaves your machine without you realizing it. Companies behind those tools may use your data to train models, sell it to third parties, or expose it in data breaches.
 
**ExcelAgentAI solves this by running 100% locally:**
- The LLM runs on your own GPU via Ollama
- FastAPI serves everything on `localhost`
- No file, no query, no result ever leaves your computer
---
 
## ✨ Features
 
- 📂 Upload and analyze Excel files through a simple web UI
- 🤖 AI agent powered by **Qwen3 14B** running locally via Ollama
- 🔁 Multi-step LangGraph workflow with interrupt/resume for user review
- 📐 Formula tool using `{ColumnName}` placeholders and pandas under the hood
- 🔍 RAG system via **ChromaDB** + `nomic-embed-text` embeddings for context-aware responses
- 💾 Download the processed Excel file when done
---
 
## 🧰 Tech stack
 
| Layer | Technology |
|---|---|
| Agent framework | LangGraph, LangChain |
| Backend API | FastAPI + Uvicorn |
| Local LLM | Ollama — `qwen3:14b` |
| Embeddings | `nomic-embed-text` via Ollama |
| Vector store | ChromaDB |
| Data processing | pandas, openpyxl |
| Package manager | uv |
 
---
 
## ⚙️ Requirements
 
- **NVIDIA GPU with CUDA** (required — the model runs on-device)
- CUDA 12.1+
- Python 3.11+
- Windows / Linux
> **Tested on:** Intel Core i7-14700F · RTX 5070 Ti 16 GB VRAM · 32 GB RAM · Windows 11
 
On machines without a CUDA-capable GPU, inference will be extremely slow or may fail entirely.
 
---
 
## 🚀 Quick start
 
### 1. Install uv
 
```bash
pip install uv
```
 
> `uv` is a fast Python package manager — a modern alternative to `pip`.
 
### 2. Install dependencies
 
```bash
uv add langchain langgraph fastapi uvicorn pandas openpyxl chromadb
```
 
### 3. Install Ollama
 
Download from [ollama.com](https://ollama.com) and follow the installer.
 
### 4. Pull the model
 
```bash
ollama pull qwen3:14b
ollama pull nomic-embed-text
```
 
### 5. Clone the repository and start the server
 
```bash
git clone https://github.com/Hop-RegularShowMuscleGuy/ExcelAgentAI.git
cd ExcelAgentAI
uvicorn agent_ai:app --reload
```
 
### 6. Open the UI
 
Open `index.html` in your browser — that's it. 🎉
 
---
 
## 📁 Project structure
 
```
ExcelAgentAI/
├── agent_ai.py            # Main FastAPI app + LangGraph agent
├── rag.py                 # RAG system — ChromaDB + nomic-embed-text
├── helper_functions.py    # Shared utilities and helper logic
├── tools.py               # Agent tools (formula apply, RAG queries, etc.)
├── static/
│   └── index.html         # Frontend UI
└── README.md
```
 
---
 
## 🗺️ Agent workflow
 
```
START → start_agent → planning → tool_user → tools → end_or_loop → results → end_agent → END
```
 
The agent pauses at checkpoints so you can review planned actions before they're applied to your file.
 
---
 
## ⚠️ Known limitations
 
- Requires a modern NVIDIA GPU (older GPUs with low VRAM may struggle with 14B models)
- First run downloads the model (~9 GB) — subsequent runs are instant
- Currently supports `.xlsx` files only
---
 
## 🤝 Contributing
 
Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.
 
---
 
## 📄 License
 
[MIT](LICENSE)
