import os
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

from google import genai

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("gemini_fetcher")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(LOG_DIR / "gemini_fetcher.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def main():
    logger.info("Starting Gemini job fetch run")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set in environment. Aborting.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    prompt_path = Path("prompts/gemini_job_agent.md")
    try:
        prompt = prompt_path.read_text()
    except OSError:
        logger.exception(f"Failed to read prompt file at {prompt_path}")
        sys.exit(1)

    model_name = "gemini-2.5-flash"
    logger.info(f"Calling Gemini (model={model_name}) with prompt from {prompt_path}")

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
    except Exception:
        logger.exception("Gemini API call failed")
        sys.exit(1)

    text = (response.text or "").strip()
    logger.info(f"Received response from Gemini ({len(text)} characters)")

    try:
        jobs = json.loads(text)
    except json.JSONDecodeError:
        logger.exception("Failed to parse Gemini response as JSON")
        logger.error(f"Raw response (truncated): {text[:2000]}")
        sys.exit(1)

    if not isinstance(jobs, list):
        logger.error(f"Expected a JSON list of jobs, got {type(jobs).__name__}")
        sys.exit(1)

    logger.info(f"Parsed {len(jobs)} jobs from Gemini response")

    output_file = Path(
        f"imports/jobs/jobs_{datetime.now().strftime('%Y_%m_%d')}.json"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_file.write_text(json.dumps(jobs, indent=2))
    except OSError:
        logger.exception(f"Failed to write output file {output_file}")
        sys.exit(1)

    logger.info(f"Saved {len(jobs)} jobs to {output_file}")
    print(f"Saved {len(jobs)} jobs to {output_file}")


if __name__ == "__main__":
    main()
