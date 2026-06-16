import os
import json
from pathlib import Path
from datetime import datetime
from google import genai

api_key = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=api_key)

prompt = Path("prompts/gemini_job_agent.md").read_text()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
)

text = response.text.strip()

jobs = json.loads(text)

output_file = Path(
    f"imports/jobs/jobs_{datetime.now().strftime('%Y_%m_%d')}.json"
)

output_file.write_text(
    json.dumps(jobs, indent=2)
)

print(f"Saved {len(jobs)} jobs to {output_file}")
