# Transfer-Encoding Header Fix

## Problem

The ELITEA proxy server was sending duplicate `Transfer-Encoding` headers in HTTP responses, causing errors like "multiple Transfer-Encoding headers" when strict HTTP clients like httpx/httpcore (used by the Anthropic Python SDK) tried to connect.

## Root Cause

The issue was in `elitea-proxy.py` line 107 where all headers from the upstream ELITEA response were copied to the Flask response:

```python
headers=dict(response.headers)  # This copied ALL headers
```

When Flask handles streaming responses, it automatically adds its own `Transfer-Encoding: chunked` header. If the upstream response also contained a `Transfer-Encoding` header, this resulted in duplicate headers.

## Solution

The fix filters out headers that Flask should manage automatically for streaming responses:

```python
# Filter headers to avoid conflicts with Flask's automatic header handling
filtered_headers = {}
headers_to_exclude = {
    'transfer-encoding',  # Flask handles this for streaming
    'content-encoding',   # Can cause conflicts with streaming  
    'connection',         # Flask manages connection headers
    'content-length'      # Flask calculates this for streaming
}

for key, value in response.headers.items():
    if key.lower() not in headers_to_exclude:
        filtered_headers[key] = value
```

## Headers Excluded

- `Transfer-Encoding`: Flask automatically sets this to "chunked" for streaming responses
- `Content-Encoding`: Can cause conflicts with Flask's response handling
- `Connection`: Flask manages connection-related headers
- `Content-Length`: Flask calculates this automatically for streaming

## Compatibility

This fix ensures compatibility with:

✅ **requests** library (already worked, but more permissive)  
✅ **httpx/httpcore** (strict HTTP client used by Anthropic SDK)  
✅ **Other strict HTTP/1.1 clients**

## Testing

Run `python test_headers.py` to verify the fix works with both requests and httpx libraries.

## HTTP/1.1 Compliance

This change ensures the server follows RFC 7230 Section 3.3.1, which states that Transfer-Encoding headers must not be duplicated and should be handled consistently.