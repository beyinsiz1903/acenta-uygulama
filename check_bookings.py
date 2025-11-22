#!/usr/bin/env python3
"""
Check today's bookings after seeding
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def main():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.hotel_pms
    
    today = datetime.now().date().isoformat()
    
    # Get today's arrivals
    arrivals = await db.bookings.find({
        'check_in': today,
        'status': {'$in': ['confirmed', 'guaranteed']}
    }).to_list(100)
    
    # Get today's departures
    departures = await db.bookings.find({
        'check_out': today,
        'status': 'checked_in'
    }).to_list(100)
    
    # Get checked in guests
    in_house = await db.bookings.find({
        'status': 'checked_in'
    }).to_list(100)
    
    # Get future bookings
    future = await db.bookings.find({
        'check_in': {'$gt': today},
        'status': {'$in': ['confirmed', 'guaranteed']}
    }).sort('check_in', 1).to_list(100)
    
    print(f"📅 BUGÜN: {today}")
    print(f"\n{'='*60}")
    print(f"📥 BUGÜN GİRİŞ YAPACAKLAR: {len(arrivals)} rezervasyon")
    print(f"{'='*60}")
    for booking in arrivals:
        print(f"  ✓ {booking.get('guest_name', 'N/A'):20} | Oda {booking.get('room_number', 'N/A'):5} | {booking['booking_number']}")
        print(f"    {booking['check_in']} → {booking['check_out']} | {booking['source']}")
    
    print(f"\n{'='*60}")
    print(f"📤 BUGÜN ÇIKIŞ YAPACAKLAR: {len(departures)} rezervasyon")
    print(f"{'='*60}")
    for booking in departures:
        print(f"  ✓ {booking.get('guest_name', 'N/A'):20} | Oda {booking.get('room_number', 'N/A'):5} | {booking['booking_number']}")
        print(f"    {booking['check_in']} → {booking['check_out']} | {booking['source']}")
    
    print(f"\n{'='*60}")
    print(f"🏨 ŞU AN KONAKLAYAN: {len(in_house)} misafir")
    print(f"{'='*60}")
    for booking in in_house[:5]:
        print(f"  ✓ {booking.get('guest_name', 'N/A'):20} | Oda {booking.get('room_number', 'N/A'):5}")
        print(f"    {booking['check_in']} → {booking['check_out']}")
    
    print(f"\n{'='*60}")
    print(f"📆 GELECEKTEKİ REZERVASYONLAR: {len(future)} rezervasyon")
    print(f"{'='*60}")
    for booking in future[:10]:
        print(f"  ✓ {booking.get('guest_name', 'N/A'):20} | Oda {booking.get('room_number', 'N/A'):5}")
        print(f"    {booking['check_in']} → {booking['check_out']} | {booking['source']}")
    
    print(f"\n{'='*60}")
    print("✅ Test verileri başarıyla oluşturuldu!")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
