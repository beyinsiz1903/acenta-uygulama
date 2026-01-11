#!/usr/bin/env python3

import asyncio
import httpx
from httpx import ASGITransport
import sys
sys.path.insert(0, '/app/backend')
from server import app
from app.utils import now_utc

async def debug_voucher():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        # Login first
        login_resp = await client.post('/api/auth/login', json={'email': 'admin@acenta.test', 'password': 'admin123'})
        print('Login response:', login_resp.status_code)
        
        if login_resp.status_code == 200:
            data = login_resp.json()
            token = data['access_token']
            user = data['user']
            org_id = user['organization_id']
            headers = {'Authorization': f'Bearer {token}'}
            
            print(f'Admin org_id: {org_id}')
            
            # Try the voucher endpoint with a non-existent booking
            resp = await client.post('/api/ops/bookings/test/voucher/issue', headers=headers, json={'issue_reason': 'INITIAL', 'locale': 'tr'})
            print('Non-existent booking response:', resp.status_code)
            if resp.status_code != 200:
                print('Error response:', resp.json())
            
            # Now let's try to create the booking and voucher data manually
            # We need to access the test database directly
            from app.db import get_db
            db = await get_db()
            
            # Create booking
            booking_doc = {
                "_id": "debug_booking",
                "organization_id": org_id,
                "agency_id": "debug_agency",
                "status": "CONFIRMED",
                "code": "DEBUG-1",
                "created_at": now_utc(),
                "customer": {"name": "Debug Customer", "email": "debug@example.com"},
                "items": [{"check_in": "2026-01-10", "check_out": "2026-01-12"}],
                "currency": "EUR",
                "amounts": {"sell": 100.0},
            }
            await db.bookings.insert_one(booking_doc)
            print('Created booking')
            
            # Create voucher template
            template_doc = {
                "organization_id": org_id,
                "key": "b2b_booking_default",
                "name": "Default B2B Booking Template",
                "html": "<html><body><h1>Voucher for {{booking_id}}</h1><p>Customer: {{customer_name}}</p></body></html>",
                "created_at": now_utc(),
            }
            await db.voucher_templates.insert_one(template_doc)
            print('Created voucher template')
            
            # Create active voucher
            voucher_doc = {
                "organization_id": org_id,
                "booking_id": "debug_booking",
                "version": 1,
                "status": "active",
                "template_key": "b2b_booking_default",
                "data_snapshot": {
                    "booking_id": "debug_booking",
                    "customer_name": "Debug Customer",
                    "status": "CONFIRMED",
                },
                "created_at": now_utc(),
                "created_by_email": "admin@acenta.test",
            }
            await db.vouchers.insert_one(voucher_doc)
            print('Created voucher')
            
            # Now try the voucher PDF endpoint
            resp = await client.post('/api/ops/bookings/debug_booking/voucher/issue', headers=headers, json={'issue_reason': 'INITIAL', 'locale': 'tr'})
            print('Voucher PDF response:', resp.status_code)
            if resp.status_code != 200:
                print('Error response:', resp.json())
            else:
                print('Success response:', resp.json())

if __name__ == '__main__':
    asyncio.run(debug_voucher())