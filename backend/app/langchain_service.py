import os
import time
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from .schema import EventExtracted, EventText

logger = logging.getLogger(__name__)


def _get_llm():
    """
    Returns the best available LLM.
    Primary: gemini-2.0-flash (Google free tier, resets daily at midnight PT)
    Fallback: groq llama-3.3-70b (free, generous limits, always available)
    """
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from langchain_groq import ChatGroq
            # Initialize Groq LLM
            # Switched to 8b to preserve rate limits for mass scraping!
            return ChatGroq(
                api_key=os.getenv("GROQ_API_KEY"),
                model="llama3-8b-8192", 
                temperature=0
            )
        except ImportError:
            pass  # langchain-groq not installed, fall through to Gemini

    return ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)


# ------------------------------------------------------------------
# 1. SCRAPER EXTRACTION CHAIN
# ------------------------------------------------------------------
scraper_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert data extraction AI for a student event aggregator focused on India.
You will be given raw markdown scraped from a hackathon or coding event listing page.
Your job is to extract structured event details and return ONLY a valid JSON object.

IMPORTANT: Only extract events of these types: "Hackathon", "Coding Competition".
Skip workshops, internships, jobs, quizzes, tech fests, or non-technical events entirely. Let me repeat: DO NOT extract workshops.

Fields to extract:
- 'title': Full name of the event (required)
- 'organization': College, company, or platform hosting it
- 'date': Event date or deadline as a human readable string (e.g. "April 20, 2026")
- 'event_type': MUST be one of: "Hackathon", "Coding Competition"
- 'location': City name where the event is held. Use "Online" if virtual.
- 'link': The full registration or event URL.
- 'quality_score': Rate the event from 1-10 based on prize pool, sponsors, and hosting institution reputation. If it seems generic, give a 5. If it has massive sponsors or rewards, give an 8+.
- 'is_open': Evaluate if registration is still open. If the markdown explicitly says "Registration Closed", "Expired", or dates are obviously in the past, return false. Otherwise true.
- 'tags': A single comma-separated string of the main tech themes (e.g., "Web3, AI, React, Open Source"). Limit to 3 tags max.

{format_instructions}""",
    ),
    ("human", "Here is the raw scraped markdown page:\n\n{markdown}"),
])



def extract_event_from_markdown(markdown: str, retries: int = 2) -> dict:
    """
    Takes raw markdown from Firecrawl and extracts a clean event dict using the LLM.
    Retries up to `retries` times with a 35-second backoff on rate limit errors.
    """
    parser = JsonOutputParser(pydantic_object=EventExtracted)
    chain = scraper_prompt | _get_llm() | parser

    for attempt in range(retries + 1):
        try:
            result = chain.invoke({
                "markdown": markdown,
                "format_instructions": parser.get_format_instructions()
            })
            return result
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if attempt < retries:
                    wait = 35 * (attempt + 1)  # 35s, 70s backoff
                    logger.warning(f"Rate limit hit. Waiting {wait}s before retry {attempt+1}...")
                    time.sleep(wait)
                    continue
            raise  # Re-raise non-rate-limit errors immediately


# ------------------------------------------------------------------
# 2. MANUAL ANALYSIS CHAIN (for /api/events/analyze endpoint)
# ------------------------------------------------------------------
manual_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a backend data extractor. Extract event details from the given text and return ONLY valid JSON."
    ),
    (
        "human",
        "Extract: name, date, location, registration_link.\n\nText: {raw_text}\n\n{format_instructions}"
    ),
])


def analyze_event_text(event: EventText) -> dict:
    """
    Manual endpoint: Accepts raw text and extracts event details.
    """
    parser = JsonOutputParser()
    chain = manual_prompt | _get_llm() | parser
    result = chain.invoke({
        "raw_text": event.raw_text,
        "format_instructions": parser.get_format_instructions()
    })
    return result
