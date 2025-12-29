#!/usr/bin/env python3
"""
Debug script to test approval process step by step
"""
import requests
import json

def debug_approval():
    base_url = "http://localhost:8001"
    
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
    if not bookings:
        print("No pending bookings found")
        return
        
    booking_id = bookings[0]['id']
    print(f"Trying to approve booking: {booking_id}")
    
    # Try to approve
    approve_response = requests.post(f"{base_url}/api/hotel/bookings/{booking_id}/approve", headers=hotel_headers)
    
    print(f"Approval response status: {approve_response.status_code}")
    print(f"Approval response: {approve_response.text}")
    
    if approve_response.status_code != 200:
        # Let's check the backend logs for more details
        print("\nLet's check if we can get more details...")

if __name__ == "__main__":
    debug_approval()