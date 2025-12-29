#!/usr/bin/env python3
"""
Debug script to inspect booking structure
"""
import requests
import json

def debug_booking():
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
    
    # Login as hotel admin
    hotel_login_response = requests.post(f"{base_url}/api/auth/login", json={
        "email": "hoteladmin@acenta.test",
        "password": "admin123"
    })
    
    if hotel_login_response.status_code != 200:
        print("Hotel login failed")
        return
        
    hotel_token = hotel_login_response.json()['access_token']
    hotel_headers = {'Authorization': f'Bearer {hotel_token}', 'Content-Type': 'application/json'}
    
    # Get pending bookings
    bookings_response = requests.get(f"{base_url}/api/hotel/bookings?status=pending", headers=hotel_headers)
    
    if bookings_response.status_code != 200:
        print("Failed to get bookings")
        return
        
    bookings = bookings_response.json()
    if bookings:
        print("Sample booking structure:")
        print(json.dumps(bookings[0], indent=2, default=str))
    else:
        print("No pending bookings found")

if __name__ == "__main__":
    debug_booking()