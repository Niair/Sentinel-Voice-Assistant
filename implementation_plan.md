# Implementation Plan - Solve AI Response Error

The goal is to fix the `ERR_EMPTY_RESPONSE` / `500` error occurring when sending messages, ensuring the AI assistant properly processes requests and streams responses.

## User Review Required

> [!IMPORTANT]
> The AI backend currently has a hardcoded model selection and might be failing due to missing environment variables or request body mismatches.

- **Backend Logs**: We need to verify the exact error message in the Python terminal when a request is made.
- **Model Compatibility**: Currently, the backend only uses `llama-3.3-70b-versatile`. We need to ensure this is acceptable or enable dynamic model loading.

## Proposed Changes

### 1. Networking Fix (Windows Localhost)
- Update `frontend/app/api/chat/route.ts` to use `127.0.0.1:8000` instead of `localhost:8000`. This avoids DNS resolution conflicts on Windows that often cause "SocketError: other side closed".

### 2. Backend Streaming Stability
- Add explicit `Connection: keep-alive` and `Cache-Control: no-cache` headers to the `StreamingResponse` in `backend/app/main.py`.
- Ensure the stream doesn't close prematurely by adding a try-except block around the iterator.

### 3. Request Formatting
- The 422 errors were fixed by mapping messages to a simple format, but we'll ensure the content is always a valid string to prevent serialization errors.

### 4. Persistence & UI Sync
- Ensure the sidebar correctly updates after a chat is saved by verifying the `mutate` calls in the frontend.

## Verification Plan

### Automated Tests
- Use `node test-backend.js` to verify the backend independently of the frontend UI.
- Check backend console output for "Chat saved" and "Streaming started" logs.

### Manual Verification
1. Send a "Hi" message in the browser.
2. Verify a thinking state or immediate text streaming.
3. Reload the page and ensure the response is still there.
