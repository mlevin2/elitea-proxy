#!/usr/bin/env python3
"""
Test script to verify the Transfer-Encoding header fix.
This simulates the conditions that cause duplicate headers.
"""

import requests
import httpx
import json
from time import sleep

def test_with_requests():
    """Test with the requests library (more permissive)"""
    print("Testing with requests library...")
    try:
        response = requests.post(
            'http://192.168.0.4:4000/v1/messages',
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 100,
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True
            },
            stream=True,
            timeout=10
        )

        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")

        # Check for duplicate Transfer-Encoding
        transfer_encoding_headers = [
            k for k in response.headers.keys()
            if k.lower() == 'transfer-encoding'
        ]

        if len(transfer_encoding_headers) > 1:
            print(f"❌ DUPLICATE Transfer-Encoding headers found: {transfer_encoding_headers}")
            return False
        else:
            print(f"✅ Transfer-Encoding headers OK: {transfer_encoding_headers}")
            return True

    except Exception as e:
        print(f"❌ requests test failed: {e}")
        return False

def test_with_httpx():
    """Test with httpx (strict HTTP client like Anthropic SDK uses)"""
    print("\nTesting with httpx library...")
    try:
        with httpx.Client() as client:
            response = client.post(
                'http://192.168.0.4:4000/v1/messages',
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 100,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": True
                },
                timeout=10
            )

            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print("✅ httpx test passed - no header conflicts")
            return True

    except Exception as e:
        print(f"❌ httpx test failed: {e}")
        return False

def test_health_endpoint():
    """Test the health endpoint"""
    print("\nTesting health endpoint...")
    try:
        response = requests.get('http://192.168.0.4:4000/health', timeout=5)
        print(f"Status Code: {response.status_code}")
        health_data = response.json()
        print(f"Health: {health_data}")
        return response.status_code < 400
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == '__main__':
    print("🔍 Testing ELITEA proxy server for header issues...")
    print("=" * 50)

    # Test health first
    health_ok = test_health_endpoint()

    if not health_ok:
        print("⚠️  Server health check failed, but continuing with header tests...")

    # Test with both libraries
    requests_ok = test_with_requests()
    httpx_ok = test_with_httpx()

    print("\n" + "=" * 50)
    print("📋 SUMMARY:")
    print(f"  Health endpoint: {'✅' if health_ok else '❌'}")
    print(f"  requests library: {'✅' if requests_ok else '❌'}")
    print(f"  httpx library: {'✅' if httpx_ok else '❌'}")

    if requests_ok and httpx_ok:
        print("🎉 All tests passed! The duplicate header issue appears to be fixed.")
    else:
        print("❌ Some tests failed. Check server logs for details.")