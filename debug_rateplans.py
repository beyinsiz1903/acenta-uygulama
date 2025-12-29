#!/usr/bin/env python3
"""
Debug script to check rate plans
"""
import requests
import json

def debug_rate_plans():
    base_url = "http://localhost:8001"
    
    # Login as admin to check rate plans
    login_response = requests.post(f"{base_url}/api/auth/login", json={
        "email": "admin@acenta.test",
        "password": "admin123"
    })
    
    if login_response.status_code != 200:
        print("Login failed")
        return
        
    admin_token = login_response.json()['access_token']
    headers = {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}
    
    # Check rate plans
    rateplans_response = requests.get(f"{base_url}/api/rateplans", headers=headers)
    
    if rateplans_response.status_code != 200:
        print(f"Rate plans request failed: {rateplans_response.status_code}")
        return
        
    rate_plans = rateplans_response.json()
    print("Available rate plans:")
    for plan in rate_plans:
        print(f"ID: {plan.get('id')}, Name: {plan.get('name')}, Active: {plan.get('is_active')}")

if __name__ == "__main__":
    debug_rate_plans()