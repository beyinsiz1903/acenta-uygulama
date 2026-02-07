#!/bin/bash
# Settlement Run API Curl Examples
# Backend URL: https://hardening-e1-e4.preview.emergentagent.com

# Step 1: Login as admin and get JWT token
echo "🔐 Step 1: Admin Login"
LOGIN_RESPONSE=$(curl -s -X POST "https://hardening-e1-e4.preview.emergentagent.com/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@acenta.test", "password": "admin123"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
echo "✅ Login successful, token: ${TOKEN:0:20}..."

echo ""
echo "=" * 60

# Step 2: GET settlements list (no params)
echo "📋 Step 2: GET settlements list (no parameters)"
curl -s -X GET "https://hardening-e1-e4.preview.emergentagent.com/api/ops/finance/settlements" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'

echo ""
echo "=" * 60

# Step 3: POST create settlement run
echo "🏗️ Step 3: POST create settlement run"
CREATE_RESPONSE=$(curl -s -X POST "https://hardening-e1-e4.preview.emergentagent.com/api/ops/finance/settlements" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"supplier_id": "test_supplier_curl_123", "currency": "EUR", "period": null}')

echo $CREATE_RESPONSE | jq '.'

# Extract settlement_id if successful
SETTLEMENT_ID=$(echo $CREATE_RESPONSE | jq -r '.settlement_id // empty')
SUPPLIER_ID="test_supplier_curl_123"

echo ""
echo "=" * 60

# Step 4: GET settlements with filters
echo "🔍 Step 4: GET settlements with supplier_id and currency filters"
curl -s -X GET "https://hardening-e1-e4.preview.emergentagent.com/api/ops/finance/settlements?supplier_id=$SUPPLIER_ID&currency=EUR" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'

echo ""
echo "=" * 60

# Step 5: Test 409 conflict (try to create another settlement with same supplier+currency)
echo "⚠️ Step 5: Test 409 conflict (duplicate settlement)"
curl -s -X POST "https://hardening-e1-e4.preview.emergentagent.com/api/ops/finance/settlements" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"supplier_id": "test_supplier_curl_123", "currency": "EUR", "period": null}' | jq '.'

echo ""
echo "🎉 Settlement Run API Curl Examples Complete!"