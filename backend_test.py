#!/usr/bin/env python3
"""
Auth Login Flow Test - Turkish Request
Testing POST /auth/login endpoint for preview backend status
"""

import asyncio
import aiohttp
import json
from datetime import datetime

# Test Configuration
BASE_URL = "https://mimari-analiz.preview.emergentagent.com/api"
TEST_CREDENTIALS = {
    "email": "demo@hotel.com",
    "password": "demo123"
}

async def test_auth_login():
    """Test auth login endpoint as requested in Turkish"""
    print("🔐 AUTH LOGIN AKIŞI TEST - PREVIEW BACKEND DURUMU")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test login endpoint
            login_url = f"{BASE_URL}/auth/login"
            print(f"📍 Testing: POST {login_url}")
            print(f"📧 Credentials: {TEST_CREDENTIALS['email']} / {TEST_CREDENTIALS['password']}")
            
            start_time = datetime.now()
            async with session.post(login_url, json=TEST_CREDENTIALS) as response:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                print(f"⏱️  Response Time: {response_time:.1f}ms")
                print(f"📊 HTTP Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract tenant information
                    tenant = data.get('tenant', {})
                    subscription_plan = tenant.get('subscription_plan') or tenant.get('plan', 'N/A')
                    features = tenant.get('features', {})
                    
                    print(f"✅ Login Successful")
                    print(f"🏨 Tenant ID: {tenant.get('id', 'N/A')}")
                    print(f"🏢 Property Name: {tenant.get('property_name', 'N/A')}")
                    print(f"📋 Subscription Plan: {subscription_plan}")
                    print(f"🔧 Features Count: {len(features)}")
                    
                    # Analyze features structure
                    print("\n📋 TENANT FEATURES ANALYSIS:")
                    print("-" * 40)
                    
                    if features:
                        # Get first 15 features for summary
                        feature_items = list(features.items())[:15]
                        
                        print("First 15 Feature Keys:")
                        for i, (key, value) in enumerate(feature_items, 1):
                            status = "✅" if value else "❌"
                            print(f"{i:2d}. {key}: {value} {status}")
                        
                        # Count true/false features
                        true_count = sum(1 for v in features.values() if v)
                        false_count = sum(1 for v in features.values() if not v)
                        
                        print(f"\n📊 Feature Summary:")
                        print(f"   Total Features: {len(features)}")
                        print(f"   Enabled (true): {true_count}")
                        print(f"   Disabled (false): {false_count}")
                        
                        # Create summary response
                        sample_features = {k: v for k, v in feature_items}
                        
                        summary = {
                            "plan": subscription_plan,
                            "sampleFeatures": sample_features,
                            "totalFeatures": len(features),
                            "enabledCount": true_count,
                            "disabledCount": false_count
                        }
                        
                        print(f"\n🎯 SUMMARY RESPONSE:")
                        print(json.dumps(summary, indent=2))
                        
                        return summary
                    else:
                        print("⚠️  No features found in tenant object")
                        return {
                            "plan": subscription_plan,
                            "sampleFeatures": {},
                            "error": "No features found"
                        }
                        
                elif response.status == 401:
                    error_data = await response.json()
                    print(f"❌ Authentication Failed: {error_data.get('detail', 'Invalid credentials')}")
                    return {
                        "error": "Authentication failed",
                        "status": response.status,
                        "detail": error_data.get('detail', 'Invalid credentials')
                    }
                else:
                    error_text = await response.text()
                    print(f"❌ HTTP {response.status}: {error_text}")
                    return {
                        "error": f"HTTP {response.status}",
                        "detail": error_text
                    }
                    
        except Exception as e:
            print(f"❌ Request Failed: {str(e)}")
            return {
                "error": "Request failed",
                "detail": str(e)
            }

async def main():
    """Main test execution"""
    print("🏨 HOTEL PMS LOGIN TENANT FEATURES TEST")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run the test
    result = await test_login_tenant_features()
    
    print("\n" + "=" * 60)
    print("🎯 FINAL RESULT:")
    print(json.dumps(result, indent=2))
    
    return result

if __name__ == "__main__":
    asyncio.run(main())