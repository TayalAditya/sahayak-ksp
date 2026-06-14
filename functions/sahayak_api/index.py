"""
Sahayak — Catalyst Advanced I/O Function (backend entry point).
Routes all HTTP requests through the FastAPI app.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.engine import config
config.load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# Import the FastAPI app
from backend.api.main import app

# Wrap FastAPI app with Mangum for serverless execution
handler = Mangum(app, lifespan="off")
