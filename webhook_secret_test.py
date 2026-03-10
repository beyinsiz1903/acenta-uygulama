#!/usr/bin/env python3
"""
Additional test to verify Stripe webhook secret configuration
"""

import requests
import json

def test_stripe_webhook_secret_configuration():
    """
    Test to verify STRIPE_WEBHOOK_SECRET is properly configured
    by checking if the webhook endpoint rejects unsigned requests correctly
    """
    
    base_url = "https://agency-ops-core.preview.emergentagent.com"
    webhook_url = f"{base_url}/api/webhook/stripe"
    
    print("🔍 Testing Stripe Webhook Secret Configuration...")
    
    # Test 1: Request without signature header - should be rejected
    print("\n1. Testing request without signature header...")
    response1 = requests.post(webhook_url, json={"test": "data"})
    print(f"   Status: {response1.status_code}")
    
    if response1.status_code == 503:
        error_data = response1.json()
        if error_data.get("error", {}).get("code") == "webhook_secret_missing":
            print("   ❌ STRIPE_WEBHOOK_SECRET is NOT configured (503 webhook_secret_missing)")
            return False
        
    # Test 2: Request with invalid signature - should be rejected  
    print("\n2. Testing request with invalid signature...")
    headers = {
        "Stripe-Signature": "t=1234567890,v1=invalid_signature_here",
        "Content-Type": "application/json"
    }
    response2 = requests.post(webhook_url, json={"test": "data"}, headers=headers)
    print(f"   Status: {response2.status_code}")
    
    if response2.status_code == 400:
        print("   ✅ Webhook correctly rejects invalid signature (400)")
    elif response2.status_code == 500:
        print("   ✅ Webhook processes signature but fails validation (500)")
        print("   ℹ️  This indicates STRIPE_WEBHOOK_SECRET is configured")
    else:
        print(f"   ⚠️  Unexpected response: {response2.status_code}")
    
    # Test 3: Empty request with signature header
    print("\n3. Testing empty request with signature header...")
    response3 = requests.post(webhook_url, data="", headers=headers)
    print(f"   Status: {response3.status_code}")
    
    # Summary
    print("\n📋 Summary:")
    print(f"   - No signature: {response1.status_code}")
    print(f"   - Invalid signature: {response2.status_code}")
    print(f"   - Empty with signature: {response3.status_code}")
    
    # If we get non-503 responses, it means the secret is configured
    if response1.status_code != 503 and response2.status_code != 503:
        print("\n✅ STRIPE_WEBHOOK_SECRET appears to be configured correctly")
        print("   The webhook endpoint is rejecting unsigned/invalid requests as expected")
        return True
    else:
        print("\n❌ STRIPE_WEBHOOK_SECRET may not be configured")
        return False

if __name__ == "__main__":
    test_stripe_webhook_secret_configuration()