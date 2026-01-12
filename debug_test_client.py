#!/usr/bin/env python3
"""Debug test to check what's happening with the test client"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import app
import httpx
from httpx import ASGITransport

async def debug_test():
    """Debug the test client setup"""
    
    # Print all routes
    print("=== ALL ROUTES ===")
    for route in app.routes:
        if hasattr(route, 'path'):
            methods = getattr(route, 'methods', ['N/A'])
            print(f"{methods} {route.path}")
    
    print("\n=== TESTING WITH ASGI TRANSPORT ===")
    
    # Test with ASGI transport (like pytest does)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
        
        # Test root
        resp = await client.get("/")
        print(f"GET /: {resp.status_code}")
        
        # Test health
        resp = await client.get("/health")
        print(f"GET /health: {resp.status_code}")
        
        # Test public quote with empty payload
        resp = await client.post("/api/public/quote", json={})
        print(f"POST /api/public/quote (empty): {resp.status_code}")
        print(f"Response: {resp.text[:200]}")
        
        # Test public checkout with empty payload
        resp = await client.post("/api/public/checkout", json={})
        print(f"POST /api/public/checkout (empty): {resp.status_code}")
        print(f"Response: {resp.text[:200]}")

if __name__ == "__main__":
    asyncio.run(debug_test())