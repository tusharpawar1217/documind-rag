# DocuMind RAG System - API Documentation

## Base URL
- Development: `http://localhost:8000`
- Production: `https://your-domain.com`

## Authentication

All protected endpoints require JWT authentication.

### Get Token (Implementation Required)
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Using Token
Include token in Authorization header:
```http
Authorization: Bearer eyJhbGc...
```

## Endpoints

### 1. Health Check

Check system health and service availability.

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "qdrant": "up",
    "gemini": "up"
  }
}
```

---

### 2. Upload Document

Upload a PDF document for processing.

```http
POST /api/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: [PDF file]
```

**Request:**
- **file**: PDF file (max 50MB)

**Response (Success):**
```json
{
  "status": "success",
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "research_paper.pdf",
  "page_count": 10,
  "chunk_count": 45,
  "chunks_by_type": {
    "text": 40,
    "table": 3,
    "image": 2
  }
}
```

**Response (Error):**
```json
{
  "detail": "File size exceeds 50MB limit"
}
```

**Rate Limit:** 10 uploads per hour per user

**Error Codes:**
- `400` - Invalid file format, size exceeded, or corrupted PDF
- `401` - Authentication required
- `429` - Rate limit exceeded
- `500` - Server error

---

### 3. Query Documents

Query documents and get answers with precise page citations.

```http
POST /api/query
Authorization: Bearer {token}
Content-Type: application/json

{
  "query": "What are the key findings about climate change?",
  "document_ids": ["doc-id-1", "doc-id-2"],
  "top_k": 5,
  "include_metadata": true,
  "min_confidence": 0.7
}
```

**Request Body:**
- **query** (required): Question to ask (max 500 characters)
- **document_ids** (optional): Filter by specific documents
- **top_k** (optional): Number of results (1-20, default: 5)
- **include_metadata** (optional): Include metadata (default: true)
- **min_confidence** (optional): Minimum confidence threshold (0-1, default: 0)

**Response:**
```json
{
  "answer": "The key findings indicate that climate change is causing significant impacts including rising temperatures [Page 5], melting ice caps [Page 12], and increased extreme weather events [Page 18].",
  "citations": [
    {
      "page_number": 5,
      "document_id": "123e4567-e89b-12d3-a456-426614174000",
      "document_name": "climate_report.pdf",
      "content": "Rising temperatures are accelerating at an unprecedented rate...",
      "relevance_score": 0.92
    },
    {
      "page_number": 12,
      "document_id": "123e4567-e89b-12d3-a456-426614174000",
      "document_name": "climate_report.pdf",
      "content": "Polar ice caps are melting faster than predicted...",
      "relevance_score": 0.88
    }
  ],
  "confidence": 0.87,
  "processing_time": 1450.5,
  "sources_used": 5
}
```

**Rate Limit:** 100 queries per hour per user

**Error Codes:**
- `400` - Invalid query, empty query, or injection attempt detected
- `401` - Authentication required
- `429` - Rate limit exceeded
- `500` - Server error

---

### 4. List Documents

Get list of all documents uploaded by the authenticated user.

```http
GET /api/documents
Authorization: Bearer {token}
```

**Response:**
```json
{
  "documents": [
    {
      "document_id": "123e4567-e89b-12d3-a456-426614174000",
      "filename": "research_paper.pdf",
      "page_count": 10,
      "status": "ready",
      "upload_date": "2024-01-15T10:30:00Z",
      "chunk_count": 45,
      "file_size": 2048576
    }
  ],
  "total": 1
}
```

**Status Values:**
- `processing` - Document is being processed
- `ready` - Document is indexed and searchable
- `error` - Processing failed
- `pending` - Waiting for retry (after rate limit)

---

### 5. Delete Document

Delete a document and all associated chunks.

```http
DELETE /api/documents/{document_id}
Authorization: Bearer {token}
```

**Path Parameters:**
- **document_id**: Document UUID

**Response:**
```json
{
  "status": "success",
  "message": "Document 123e4567-e89b-12d3-a456-426614174000 deleted"
}
```

**Error Codes:**
- `403` - Not authorized to delete this document
- `404` - Document not found
- `500` - Server error

---

### 6. Get Document Status

Check processing status of a document.

```http
GET /api/documents/{document_id}/status
Authorization: Bearer {token}
```

**Path Parameters:**
- **document_id**: Document UUID

**Response:**
```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "ready",
  "page_count": 10,
  "chunk_count": 45,
  "error_message": null
}
```

---

## Data Models

### Citation
```typescript
{
  page_number: number;        // Page number (1-indexed)
  document_id: string;        // Document UUID
  document_name: string;      // Original filename
  content: string;           // Content snippet (truncated to 200 chars)
  relevance_score: number;   // Relevance score (0-1)
}
```

### QueryResponse
```typescript
{
  answer: string;            // Generated answer with [Page X] citations
  citations: Citation[];     // List of page citations
  confidence: number;        // Confidence score (0-1)
  processing_time: number;   // Processing time in milliseconds
  sources_used: number;      // Number of chunks used in context
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

- **200 OK** - Request successful
- **400 Bad Request** - Invalid request parameters
- **401 Unauthorized** - Authentication required or token invalid
- **403 Forbidden** - Not authorized to access resource
- **404 Not Found** - Resource not found
- **413 Payload Too Large** - File size exceeds limit
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error
- **503 Service Unavailable** - Service temporarily unavailable

## Rate Limits

### Per-User Limits
- **Uploads**: 10 per hour
- **Queries**: 100 per hour

### Global Limits
- **Total API Requests**: 1000 per minute

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

### Rate Limit Exceeded Response
```json
{
  "detail": "Rate limit exceeded. Try again in 3600 seconds."
}
```

## Examples

### cURL Examples

**Upload Document:**
```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

**Query Documents:**
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main conclusions?",
    "top_k": 5
  }'
```

**Delete Document:**
```bash
curl -X DELETE http://localhost:8000/api/documents/DOC_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Python Example

```python
import requests

# Upload document
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/upload',
        headers={'Authorization': f'Bearer {token}'},
        files={'file': f}
    )
    result = response.json()
    print(f"Document ID: {result['document_id']}")

# Query documents
response = requests.post(
    'http://localhost:8000/api/query',
    headers={'Authorization': f'Bearer {token}'},
    json={
        'query': 'What are the key findings?',
        'top_k': 5
    }
)
result = response.json()
print(f"Answer: {result['answer']}")
print(f"Citations: {len(result['citations'])} pages")
```

### JavaScript Example

```javascript
// Upload document
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const uploadResponse = await fetch('http://localhost:8000/api/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
const uploadResult = await uploadResponse.json();

// Query documents
const queryResponse = await fetch('http://localhost:8000/api/query', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'What are the main conclusions?',
    top_k: 5
  })
});
const queryResult = await queryResponse.json();
console.log('Answer:', queryResult.answer);
```

## Interactive Documentation

The API provides interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- Browse all available endpoints
- View request/response schemas
- Test API calls directly from the browser
- Download OpenAPI specification

## Webhooks (Future Enhancement)

Planned support for webhooks to notify when document processing completes:

```json
POST https://your-callback-url.com/webhook
Content-Type: application/json

{
  "event": "document.processed",
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "ready",
  "timestamp": "2024-01-15T10:35:00Z"
}
```

## SDK Support (Future Enhancement)

Planned official SDKs:
- Python SDK
- JavaScript/TypeScript SDK
- Java SDK
- Go SDK
