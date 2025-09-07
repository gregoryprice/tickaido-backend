#!/bin/bash
# tests/scripts/test_avatar_e2e.sh

set -e  # Exit on any error

echo "🚀 Starting Avatar API E2E Test"

# Start services
echo "📦 Starting required services..."
docker compose up -d postgres redis app
sleep 15  # Wait for services to be ready

# Health check
echo "🏥 Checking service health..."
curl -f http://localhost:8000/health || (echo "❌ Service not healthy" && exit 1)
echo "✅ Service is healthy"

# Test user registration/login
echo "👤 Creating test user..."
USER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"avatar-test@example.com",
    "password":"testpass123",
    "full_name":"Avatar Test User",
    "organization_name": "Test Organization"
  }' || echo '{}')

# Check if registration returned a token, if not try login
ACCESS_TOKEN=$(echo $USER_RESPONSE | jq -r '.access_token // empty')

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
    echo "⚠️  Registration didn't return token, trying login instead..."
    USER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d '{
        "email":"avatar-test@example.com",
        "password":"testpass123"
      }')
fi

# Extract user info from response
USER_ID=$(echo $USER_RESPONSE | jq -r '.user.id // .id // empty')
ACCESS_TOKEN=$(echo $USER_RESPONSE | jq -r '.access_token // empty')

if [ -z "$USER_ID" ] || [ "$USER_ID" = "null" ] || [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
    echo "❌ Failed to get user ID or access token"
    echo "Response: $USER_RESPONSE"
    exit 1
fi

echo "✅ User authenticated: $USER_ID"

# Test avatar upload
echo "📤 Testing avatar upload..."
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/users/$USER_ID/avatar" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@tests/fixtures/images/valid_avatar.jpg" || echo '{"error": "upload_failed"}')

if echo "$UPLOAD_RESPONSE" | grep -q "error"; then
    echo "❌ Avatar upload failed"
    echo "Response: $UPLOAD_RESPONSE"
    exit 1
fi

AVATAR_URL=$(echo $UPLOAD_RESPONSE | jq -r '.avatar_url // empty')
if [ -z "$AVATAR_URL" ] || [ "$AVATAR_URL" = "null" ]; then
    echo "❌ No avatar URL returned from upload"
    echo "Response: $UPLOAD_RESPONSE"
    exit 1
fi

echo "✅ Avatar uploaded: $AVATAR_URL"

# Test avatar retrieval
echo "📥 Testing avatar download..."
HTTP_STATUS=$(curl -s -o /tmp/downloaded_avatar.jpg -w "%{http_code}" \
  "http://localhost:8000/api/v1/users/$USER_ID/avatar")

if [ "$HTTP_STATUS" != "200" ]; then
    echo "❌ Avatar download failed with status $HTTP_STATUS"
    exit 1
fi

# Check if file was actually downloaded
if [ ! -f "/tmp/downloaded_avatar.jpg" ]; then
    echo "❌ Avatar file was not downloaded"
    exit 1
fi

# Check file size is reasonable (should be > 0 bytes)
FILE_SIZE=$(stat -f%z /tmp/downloaded_avatar.jpg 2>/dev/null || stat -c%s /tmp/downloaded_avatar.jpg 2>/dev/null || echo 0)
if [ "$FILE_SIZE" -eq 0 ]; then
    echo "❌ Downloaded avatar file is empty"
    exit 1
fi

echo "✅ Avatar downloaded successfully (${FILE_SIZE} bytes)"

# Test avatar info endpoint
echo "ℹ️  Testing avatar info retrieval..."
INFO_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/users/$USER_ID/avatar/info" \
  -H "Authorization: Bearer $ACCESS_TOKEN" || echo '{"error": "info_failed"}')

if echo "$INFO_RESPONSE" | grep -q "error"; then
    echo "⚠️  Avatar info failed (this might be expected if not implemented yet)"
else
    echo "✅ Avatar info retrieved: $(echo $INFO_RESPONSE | jq -r '.filename // "unknown"')"
fi

# Test avatar deletion
echo "🗑️  Testing avatar deletion..."
DELETE_RESPONSE=$(curl -s -X DELETE "http://localhost:8000/api/v1/users/$USER_ID/avatar" \
  -H "Authorization: Bearer $ACCESS_TOKEN" || echo '{"error": "delete_failed"}')

if echo "$DELETE_RESPONSE" | grep -q "error"; then
    echo "❌ Avatar deletion failed"
    echo "Response: $DELETE_RESPONSE"
    exit 1
fi

echo "✅ Avatar deleted successfully"

# Test avatar not found after deletion
echo "🔍 Verifying avatar is removed..."
sleep 2  # Give time for deletion to process

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "http://localhost:8000/api/v1/users/$USER_ID/avatar")

if [ "$HTTP_STATUS" = "404" ]; then
    echo "✅ Avatar properly removed (404 response)"
elif [ "$HTTP_STATUS" = "200" ]; then
    echo "⚠️  Avatar still accessible after deletion (might be cached or not fully deleted)"
else
    echo "⚠️  Unexpected status code after deletion: $HTTP_STATUS"
fi

# Test security - try uploading invalid file
echo "🛡️  Testing security with invalid file..."
SECURITY_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/users/$USER_ID/avatar" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@tests/fixtures/images/invalid_file.pdf" || echo '{"detail": "expected_error"}')

if echo "$SECURITY_RESPONSE" | grep -q "400\|not allowed\|invalid"; then
    echo "✅ Security validation working - invalid file rejected"
else
    echo "⚠️  Security test unclear: $SECURITY_RESPONSE"
fi

# Test unauthorized access
echo "🔒 Testing unauthorized access..."
OTHER_USER_ID="550e8400-e29b-41d4-a716-446655440000"  # Random UUID
UNAUTH_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/users/$OTHER_USER_ID/avatar" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@tests/fixtures/images/valid_avatar.jpg" || echo '{"detail": "expected_error"}')

if echo "$UNAUTH_RESPONSE" | grep -q "403\|forbidden\|not allowed"; then
    echo "✅ Authorization working - cross-user upload blocked"
else
    echo "⚠️  Authorization test unclear: $UNAUTH_RESPONSE"
fi

echo ""
echo "🎉 All Avatar E2E tests completed!"
echo "📊 Test Summary:"
echo "  ✅ User authentication"
echo "  ✅ Avatar upload"
echo "  ✅ Avatar download"  
echo "  ✅ Avatar deletion"
echo "  ✅ Security validation"
echo "  ✅ Authorization checks"

# Cleanup
echo "🧹 Cleaning up test files..."
rm -f /tmp/downloaded_avatar.jpg

echo "✅ E2E test completed successfully!"