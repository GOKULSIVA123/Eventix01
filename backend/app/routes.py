from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from .database import get_db
from . import models, schema
from .langchain_service import analyze_event_text
from .scraper_engine import UniversalScraper, SOURCES_CONFIG

router = APIRouter(prefix="/api/events", tags=["events"])

# ------------------------------------------------------------------
# HELLO WORLD - Connection test
# ------------------------------------------------------------------
@router.get("/hello")
def get_hello():
    return {"message": "Hello from EventHive FastAPI Server!"}


# ------------------------------------------------------------------
# GET ALL EVENTS - List everything stored in the DB
# ------------------------------------------------------------------
@router.get("/", response_model=list[schema.EventResponse])
def get_all_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # 💥 THE FILTER: Only return events that AI confirmed are still open for registration
    events = db.query(models.Event).filter(models.Event.is_open == True).offset(skip).limit(limit).all()
    return events


# ------------------------------------------------------------------
# SCRAPE SINGLE SOURCE - Trigger scraper for one site
# ------------------------------------------------------------------
@router.post("/scrape/{source_name}")
def scrape_source(source_name: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Triggers the full scrapen pipeline for a single source.
    Valid source names: unstop, devfolio, knowafest
    Uses BackgroundTasks so the HTTP response returns immediately.
    """
    valid_sources = list(SOURCES_CONFIG.keys())
    if source_name not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source '{source_name}'. Valid sources: {valid_sources}"
        )

    def run_scraper():
        scraper = UniversalScraper()
        summary = scraper.run(source_name, db)
        print(f"[SCRAPE DONE] {summary}")

    background_tasks.add_task(run_scraper)
    return {
        "message": f"Scraping '{source_name}' started in background.",
        "tip": "Check your server terminal logs to see progress."
    }


# ------------------------------------------------------------------
# SCRAPE ALL SOURCES - Trigger scraper for all sites at once
# ------------------------------------------------------------------
@router.post("/scrape-all")
def scrape_all_sources(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Triggers the full scrape pipeline for ALL configured sources.
    """
    def run_all():
        scraper = UniversalScraper()
        for source_name in SOURCES_CONFIG.keys():
            print(f"[STARTING] Scraping {source_name}...")
            summary = scraper.run(source_name, db)
            print(f"[DONE] {summary}")

    background_tasks.add_task(run_all)
    return {"message": "Scraping all sources started in background."}


# ------------------------------------------------------------------
# MANUAL ANALYZE - Paste raw event text and get structured data back
# ------------------------------------------------------------------
@router.post("/analyze")
async def analyze_event(event: schema.EventText):
    """
    Accepts raw event text and uses Gemini to extract structured fields.
    Does NOT save to DB - useful for testing the LangChain extraction.
    """
    result = analyze_event_text(event)
    return result
