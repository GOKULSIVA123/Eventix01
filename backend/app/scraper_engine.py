import json
import os
import time
import re
import logging
from pathlib import Path
from firecrawl import Firecrawl  # v4: class renamed from FirecrawlApp to Firecrawl
from sqlalchemy.orm import Session
from .models import Event
from .schema import EventCreate
from .langchain_service import extract_event_from_markdown


logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
# Load the sources_config.json rulebook once at module load time
# ----------------------------------------------------------------
_config_path = Path(__file__).parent / "sources_config.json"
with open(_config_path, "r") as f:
    SOURCES_CONFIG: dict = json.load(f)


class UniversalScraper:
    """
    A site-agnostic event scraper powered by Firecrawl and LangChain.
    Reads scraping rules from sources_config.json.
    """

    def __init__(self):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY is not set in your .env file.")
        # v4: Use Firecrawl class (not FirecrawlApp)
        self.app = Firecrawl(api_key=api_key)

    # ------------------------------------------------------------------
    # PHASE 1: Discover relevant event links from a source
    # ------------------------------------------------------------------
    def map_links(self, source_name: str, db: Session) -> list[str]:
        """
        Uses firecrawl.map() to discover all event URLs from a source.
        Filters using the include_paths rules from sources_config.json.
        """
        config = SOURCES_CONFIG.get(source_name)
        if not config:
            raise ValueError(f"Source '{source_name}' not found in sources_config.json")

        if source_name == "knowafest":
            logger.info(f"[{source_name}] Performing direct markdown table scrape on: {config['base_url']}")
            # Scrape the page physically to get the Markdown
            result = self.app.scrape(config["base_url"], formats=["markdown"])
            
            # Extract markdown from the v4 API response object or dict
            markdown_text = getattr(result, "markdown", None)
            if not markdown_text and hasattr(result, "get"):
                markdown_text = result.get("markdown", "")
            
            # Regex to find all markdown format links: [Text](URL)
            all_found = re.findall(r'\]\((https?://[^)]+)\)', markdown_text or "")
            all_links = list(set(all_found)) # remove duplicates
        else:
            logger.info(f"[{source_name}] Mapping links from: {config['base_url']}")
            # v4 API: map(url=..., limit=...)  — no 'params' wrapper
            result = self.app.map(url=config["base_url"], limit=100)

            # DEBUG: Print the raw result so we can see its exact type and structure
            print(f"[{source_name}] RAW map() result type: {type(result)}")

            # v4 returns MapData with a list of LinkResult objects (not plain strings!)
            raw_links = []
            if hasattr(result, "links") and result.links:
                raw_links = result.links
            elif isinstance(result, list):
                raw_links = result

            # Extract .url strings from LinkResult objects
            all_links = [
                link.url if hasattr(link, "url") else str(link)
                for link in raw_links
                if link is not None
            ]

        print(f"[{source_name}] Total links found: {len(all_links)}")
        logger.info(f"[{source_name}] Total links found: {len(all_links)}")

        # DEBUG: Print first 10 links so we can see what Firecrawl returns
        for i, link in enumerate(all_links[:10]):
            print(f"[{source_name}] Sample link {i+1}: {link}")


        # Filter links based on the include_paths rules from JSON
        include_paths = config.get("include_paths", [])
        if include_paths:
            filtered = [
                link for link in all_links
                if any(self._matches_path(link, pattern) for pattern in include_paths)
            ]
        else:
            filtered = all_links  # no filter = take all

        print(f"[{source_name}] After initial filter: {len(filtered)} / {len(all_links)} links")
        
        # --- NEW LOGIC: Remove links already inside the database ---
        existing_links = {evt.link for evt in db.query(Event.link).all()}
        unseen_links = [l for l in filtered if l not in existing_links]
        print(f"[{source_name}] After checking database, New Unseen Links: {len(unseen_links)}")
        
        # --- NEW LOGIC: Prioritize Hackathons ---
        # Sort so that URLs containing 'hack' or 'coding' appear first in the slice
        def url_priority(u: str):
            lower_u = u.lower()
            if 'hack' in lower_u or 'code' in lower_u or 'coding' in lower_u:
                return 0
            return 1
            
        unseen_links.sort(key=url_priority)
        
        # Now we can safely grab the top 10 unseen & prioritized links!
        sliced_links = unseen_links[:10]

        # DEBUG: Print all targets so the user can verify them
        for j, filt_link in enumerate(sliced_links):
            print(f"[{source_name}] Target Batch #{j+1}: {filt_link}")
            
        logger.info(f"[{source_name}] Supplying {len(sliced_links)} fresh links to scraper.")
        return sliced_links




    # ------------------------------------------------------------------
    # PHASE 2: Scrape the clean markdown content from a single URL
    # ------------------------------------------------------------------
    def scrape_content(self, source_name: str, url: str) -> str | None:
        """
        Scrapes a single event page URL using Firecrawl.
        Returns clean markdown string.
        Note: wait_for is handled via actions in v4.
        """
        config = SOURCES_CONFIG.get(source_name, {})
        wait_for = config.get("wait_for", 0)

        try:
            if wait_for > 0:
                # v4: Use actions to wait before scraping JS-heavy sites
                result = self.app.scrape(
                    url,
                    formats=["markdown"],
                    actions=[{"type": "wait", "milliseconds": wait_for}]
                )
            else:
                # v4: Simple scrape for plain HTML sites like Knowafest
                result = self.app.scrape(url, formats=["markdown"])

            # v4 returns a ScrapeResponse object
            if hasattr(result, "markdown"):
                return result.markdown
            # Fallback: dict-style access (AsyncFirecrawl returns dict)
            if hasattr(result, "get"):
                return result.get("markdown", None)
            return None

        except Exception as e:
            logger.error(f"[{source_name}] Failed to scrape {url}: {e}")
            return None

    # ------------------------------------------------------------------
    # PHASE 3: Parse markdown into a structured Event via LangChain
    # ------------------------------------------------------------------
    def extract_event(self, markdown: str, source_name: str, url: str) -> EventCreate | None:
        """
        Pushes raw markdown through the LangChain LCEL chain (Groq / Gemini).
        """
        try:
            extracted = extract_event_from_markdown(markdown)

            # Some LLMs return a LIST when a page contains multiple things
            if isinstance(extracted, list):
                if not extracted:
                    logger.warning(f"[{source_name}] AI returned empty list for {url}")
                    return None
                extracted = extracted[0]

            if not isinstance(extracted, dict):
                logger.warning(f"[{source_name}] Unexpected AI output type: {type(extracted)}")
                return None

            # STRICT PYTHON GUARD: Do not trust the AI! Only allow valid Hackathons/Coding Comps
            evt_type = extracted.get("event_type", "")
            if evt_type not in ["Hackathon", "Coding Competition"]:
                logger.warning(f"[{source_name}] Tossed non-hackathon event: {extracted.get('title')} (Labeled as: {evt_type})")
                return None

            # Fallback for link
            if not extracted.get("link"):
                extracted["link"] = url
            extracted["source"] = source_name
            
            return EventCreate(**extracted)
        except Exception as e:
            logger.error(f"[{source_name}] AI extraction failed for {url}: {e}")
            return None




    # ------------------------------------------------------------------
    # PHASE 4: Save to SQLite with duplicate check on link field
    # ------------------------------------------------------------------
    def save_event(self, db: Session, event_data: EventCreate) -> Event | None:
        """
        Checks if the event link already exists in DB (dedup).
        If new, inserts and returns the new Event row.
        """
        existing = db.query(Event).filter(Event.link == event_data.link).first()
        if existing:
            logger.info(f"[SKIP] Already in DB: {event_data.link}")
            return None

        new_event = Event(**event_data.model_dump())
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        logger.info(f"[SAVED] {new_event.title}")
        return new_event

    # ------------------------------------------------------------------
    # MASTER METHOD: Run a full scrape pipeline for a given source
    # ------------------------------------------------------------------
    def run(self, source_name: str, db: Session) -> dict:
        """
        Full pipeline: map → scrape → extract → save.
        Returns a summary of results.
        """
        summary = {"source": source_name, "scraped": 0, "saved": 0, "skipped": 0, "errors": 0}

        links = self.map_links(source_name, db)

        for url in links:
            summary["scraped"] += 1
            markdown = self.scrape_content(source_name, url)
            if not markdown:
                summary["errors"] += 1
                continue

            event_data = self.extract_event(markdown, source_name, url)
            if not event_data:
                summary["errors"] += 1
                # Brief pause even on failure to avoid burst rate limiting
                time.sleep(1)
                continue

            saved = self.save_event(db, event_data)
            if saved:
                summary["saved"] += 1
            else:
                summary["skipped"] += 1

            # Throttle: 1.5s between Gemini calls → stays under free tier rate limit
            time.sleep(1.5)

        return summary


    # ------------------------------------------------------------------
    # HELPER: Wildcard path matching for include_paths filter
    # ------------------------------------------------------------------
    def _matches_path(self, url: str, pattern: str) -> bool:
        """
        Simple wildcard matcher.
        '*college-fests*' matches any URL containing 'college-fests'.
        '/hackathons/*' matches any URL that contains '/hackathons/'.
        """
        clean = pattern.replace("*", "")
        return clean in url
