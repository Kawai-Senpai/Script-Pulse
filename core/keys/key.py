from __future__ import annotations

import os

from dotenv import load_dotenv


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

load_dotenv(os.path.join(ROOT_DIR, ".env"))

environment = os.getenv("ENVIRONMENT", "development")

load_dotenv(os.path.join(ROOT_DIR, f".env.{environment}"))

openai_api_key = os.getenv("OPENAI_API_KEY")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
