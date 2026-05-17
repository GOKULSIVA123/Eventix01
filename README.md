# Eventix (EventHive)

Eventix is an automated, full-stack event discovery platform that actively scrapes, extracts, and serves information about upcoming Hackathons and Coding Competitions from various platforms (like Unstop, Devfolio, and Knowafest). 

## 🚀 Features

* **Universal Scraping Engine**: Powered by **Firecrawl (v4)**, the backend maps source websites to discover event links and scrapes the content cleanly into Markdown.
* **AI-Powered Extraction**: Uses **LangChain** integrated with LLMs (Groq/Gemini) to parse the raw Markdown and extract structured data (Event Name, Date, Location, Link, etc.).
* **Smart Filtering**: Automatically filters out non-relevant events and strictly ensures only "Hackathons" or "Coding Competitions" are saved.
* **Automated Cron Jobs**: Uses `apscheduler` to run a daily background task at 2:00 AM to fetch new events without manual intervention.
* **RESTful API**: Built with **FastAPI**, serving the scraped events via fast, async endpoints.
* **Modern Frontend**: Built using **React + Vite**, consuming the FastAPI backend to display events beautifully.
* **Persistent Storage**: Uses **SQLite** via SQLAlchemy to deduplicate and store event records.

## 🛠️ Tech Stack

**Backend:**
* [FastAPI](https://fastapi.tiangolo.com/) - Web framework
* [Firecrawl](https://www.firecrawl.dev/) - Web scraping and link mapping
* [LangChain](https://python.langchain.com/) - LLM orchestration for structured data extraction
* [SQLAlchemy](https://www.sqlalchemy.org/) - ORM for SQLite database
* [APScheduler](https://apscheduler.readthedocs.io/) - Background cron jobs

**Frontend:**
* [React](https://react.dev/) + [Vite](https://vitejs.dev/) - UI and Build Tool
* CSS - Styling

## 📂 Project Structure

```
Eventix/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── database.py         # SQLAlchemy Setup
│   │   ├── langchain_service.py # LangChain extraction logic
│   │   ├── main.py             # FastAPI App & Cron Jobs
│   │   ├── models.py           # Database Models
│   │   ├── routes.py           # API Endpoints
│   │   ├── schema.py           # Pydantic Models
│   │   ├── scraper_engine.py   # Firecrawl + Pipeline Logic
│   │   └── sources_config.json # Rulebook for scraping sources
│   ├── requirements.txt
│   └── test.db                 # SQLite Database
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main React Component
│   │   ├── index.css           # Global Styles
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── .gitignore
```

## ⚙️ Setup & Installation

### 1. Backend Setup

```bash
cd backend
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file and add your API Keys:
# FIRECRAWL_API_KEY=your_firecrawl_key
# GROQ_API_KEY=your_groq_key
# GEMINI_API_KEY=your_gemini_key

# Run the FastAPI server
uvicorn app.main:app --reload
```

### 2. Frontend Setup

```bash
cd frontend
# Install dependencies
npm install

# Start the development server
npm run dev
```

## 🧠 How the Scraper Works (scraper_engine.py)

1. **Mapping Phase**: `Firecrawl.map()` discovers all sub-links from a target source base URL.
2. **Filtering Phase**: Links are filtered using wildcard `include_paths` from `sources_config.json`. We also deduplicate links already existing in the database.
3. **Scraping Phase**: `Firecrawl.scrape()` navigates to the target URLs (utilizing wait actions for JS-heavy sites) and returns clean Markdown.
4. **Extraction Phase**: The Markdown is sent through a LangChain pipeline where an LLM structures the data and verifies if it is actually a coding competition.
5. **Storage Phase**: Valid events are saved to the local SQLite database.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.
