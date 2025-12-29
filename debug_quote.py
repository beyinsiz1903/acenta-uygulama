#!/usr/bin/env python3
"""
Debug script to test quote response
"""
import requests
import json

def debug_quote():
    base_url = "http://localhost:8001"
    
    # Login as agency
    login_response = requests.post(f"{base_url}/api/auth/login", json={
        "email": "agency1@demo.test",
        "password": "agency123"
    })
    
    if login_response.status_code != 200:
        print("Login failed")
        return
        
    agency_token = login_response.json()['access_token']
    headers = {'Authorization': f'Bearer {agency_token}', 'Content-Type': 'application/json'}
    
    # Create a search/quote
    search_data = {
        "hotel_id": "b7045d87-8d14-494d-84f5-63cd660058db",
        "check_in": "2026-03-15",
        "check_out": "2026-03-17",
        "occupancy": {"adults": 2, "children": 0}
    }
    
    search_response = requests.post(f"{base_url}/api/agency/search", json=search_data, headers=headers)
    
    if search_response.status_code != 200:
        print(f"Search failed: {search_response.status_code} - {search_response.text}")
        return
        
    search_result = search_response.json()
    print("Search/Quote result:")
    print(json.dumps(search_result, indent=2, default=str))

if __name__ == "__main__":
    debug_quote()