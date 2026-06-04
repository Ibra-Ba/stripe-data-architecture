from dotenv import load_dotenv
import os


load_dotenv()

DB_URL = os.getenv("NEONDB_URL")

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF"]
COUNTRIES  = ["US", "FR", "DE", "GB", "JP", "ES", "IT", "NL"]
CATEGORIES = ["ecommerce", "saas", "marketplace", "retail", "travel"]
DEVICES    = ["mobile", "desktop", "tablet"]
STATUSES   = ["success", "success", "success", "failed", "refunded"] 