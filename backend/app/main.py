from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load .env FIRST before any other local imports that may need the keys
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, SessionLocal
from .routes import router
from apscheduler.schedulers.background import BackgroundScheduler
from .scraper_engine import UniversalScraper

def scheduled_scrape():
    print("[CRON] Triggering automated background scrape...")
    db = SessionLocal()
    scraper = UniversalScraper()
    # We scrape all active sources configured
    sources = ["unstop", "devfolio", "knowafest"]
    for source in sources:
        try:
            scraper.run(source, db)
        except Exception as e:
            print(f"[CRON] Error scraping {source}: {e}")
    db.close()
    print("[CRON] Automated background scrape complete.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up EventHive... Creating database tables.")
    Base.metadata.create_all(bind=engine)
    
    # Start Cron Scheduler
    scheduler = BackgroundScheduler()
    # Run the scrape automatically every day at 2:00 AM
    scheduler.add_job(scheduled_scrape, "cron", hour=2, minute=0)
    scheduler.start()
    print("✅ Cron Scheduler started. Next scrape at 2:00 AM.")
    
    yield  # Server runs here
    
    print("Shutting down EventHive... Cleaning up resources.")
    scheduler.shutdown()


app = FastAPI(title="EventHive API", lifespan=lifespan)

# Configure CORS
origins = [
    "http://localhost:5173",  
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router containing our endpoints
app.include_router(router)
