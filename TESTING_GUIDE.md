# DocuMind RAG - Manual Testing Guide

## 🚀 System Status

✅ **Backend Server**: Running on http://localhost:8000  
✅ **Frontend Server**: Running on http://localhost:5173  
✅ **API Health**: Healthy

---

## 📋 Testing Instructions

### **Step 1: Access the Application**

Open your web browser and navigate to:
```
http://localhost:5173
```

You should see the DocuMind homepage with:
- Welcome message
- Navigation menu (Home, Upload, Search, Documents)
- Connection status indicator (should show "Connected")

---

### **Step 2: Upload a PDF Document**

1. **Navigate to Upload Page**
   - Click "Upload" in the navigation menu
   - Or go directly to: http://localhost:5173/upload

2. **Prepare a PDF File**
   - Use any PDF document from your computer
   - Recommended: Technical documentation, research papers, or articles
   - Maximum size: 50MB

3. **Upload Process**
   - Click "Choose File" or drag & drop your PDF
   - Click "Upload Document"
   - Wait for processing confirmation
   - You should see: "Document uploaded and processed successfully"

---

### **Step 3: Search and Query**

1. **Navigate to Search Page**
   - Click "Search" in the navigation menu
   - Or go directly to: http://localhost:5173/search

2. **Enter Your Question**
   - Type a question related to your uploaded document
   - Examples:
     - "What is the main topic of this document?"
     - "Summarize the key findings"
     - "What are the conclusions?"

3. **View Results**
   - Click "Search" button
   - Wait for AI to process your query
   - You'll see:
     - **AI Response**: Generated answer based on document content
     - **Search Results**: Relevant chunks from the document with scores
     - **Source Information**: Which document each result came from

---

### **Step 4: Manage Documents**

1. **Navigate to Documents Page**
   - Click "Documents" in the navigation menu
   - Or go directly to: http://localhost:5173/documents

2. **View Uploaded Documents**
   - See all uploaded documents
   - View document statistics
   - Check number of chunks per document

3. **Delete Documents** (if needed)
   - Click "Delete" button next to any document
   - Confirm deletion
   - Document and all its chunks will be removed

---

## 🧪 API Testing (Alternative)

If you prefer testing via API directly:

### **1. Health Check**
```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/health -UseBasicParsing | ConvertTo-Json
```

Expected response:
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "service": "DocuMind RAG Test"
}
```

### **2. Upload PDF via API**
```powershell
$pdfPath = "C:\path\to\your\document.pdf"
$uri = "http://localhost:8000/api/v1/documents/upload"

curl.exe -X POST $uri -F "file=@$pdfPath"
```

### **3. Query Documents**
```powershell
$body = @{
    query = "What is the main topic?"
    top_k = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/search/query" `
    -Method POST `
    -Body $body `
    -ContentType "application/json" | ConvertTo-Json -Depth 10
```

### **4. List Documents**
```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/documents -UseBasicParsing | ConvertTo-Json
```

### **5. Get Statistics**
```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/documents/stats -UseBasicParsing | ConvertTo-Json
```

---

## 🎯 Example Test Scenarios

### **Scenario 1: Research Paper Analysis**
1. Upload a research paper PDF
2. Ask questions like:
   - "What research methodology was used?"
   - "What are the main findings?"
   - "Who are the authors?"
   - "What are the limitations mentioned?"

### **Scenario 2: Technical Documentation**
1. Upload technical documentation or manual
2. Ask questions like:
   - "How do I install this software?"
   - "What are the system requirements?"
   - "Explain the configuration options"
   - "What are the troubleshooting steps?"

### **Scenario 3: Legal Document Review**
1. Upload a legal document or contract
2. Ask questions like:
   - "What are the key terms?"
   - "What are the obligations of each party?"
   - "What is the termination clause?"
   - "Are there any penalty provisions?"

---

## 📊 What to Observe

### **During Upload:**
- ✅ File validation (PDF only)
- ✅ Progress indication
- ✅ Success/error messages
- ✅ Document metadata display

### **During Search:**
- ✅ Query processing time
- ✅ Number of results returned
- ✅ Relevance scores (0-1, higher is better)
- ✅ Source attribution
- ✅ AI-generated response quality

### **Performance Metrics:**
- Upload time: ~2-5 seconds per PDF
- Search time: ~1-3 seconds per query
- Results: Top 5 most relevant chunks
- Relevance threshold: 0.5 (configurable)

---

## 🔧 Current Implementation

**Note**: This is a test server with simplified features:
- ✅ PDF text extraction (PyMuPDF)
- ✅ Simple paragraph-based chunking
- ✅ In-memory storage (data lost on restart)
- ✅ Keyword-based search (for testing)
- ⚠️ **No embeddings** (full RAG pipeline available but not active)
- ⚠️ **No vector similarity** (simple keyword matching)
- ⚠️ **No persistent storage** (documents cleared on restart)

**For Full RAG Features**: Start the main server (requires Qdrant and Gemini API):
```powershell
python backend/main.py
```

---

## 🐛 Troubleshooting

### **Backend Not Responding**
```powershell
# Check if server is running
Get-Process python | Where-Object {$_.MainWindowTitle -like "*test_server*"}

# Restart backend
cd "C:\Users\pawar\OneDrive\Desktop\git projects\new rag\backend"
python test_server.py
```

### **Frontend Not Loading**
```powershell
# Check if Vite is running
Get-Process node

# Restart frontend
cd "C:\Users\pawar\OneDrive\Desktop\git projects\new rag\frontend"
npm run dev
```

### **CORS Errors**
- Ensure both servers are running
- Clear browser cache
- Check browser console for detailed errors

### **Upload Fails**
- Verify file is a valid PDF
- Check file size < 50MB
- Look at backend terminal for error messages

---

## 📝 Test Checklist

- [ ] Backend health check passes
- [ ] Frontend loads successfully
- [ ] Connection status shows "Connected"
- [ ] Can navigate between pages
- [ ] Can upload a PDF document
- [ ] Upload shows success message
- [ ] Document appears in documents list
- [ ] Can search uploaded documents
- [ ] Search returns relevant results
- [ ] AI response is generated
- [ ] Source attribution is displayed
- [ ] Can delete documents
- [ ] Statistics update correctly

---

## 🎉 Success Criteria

Your system is working correctly if:
1. ✅ You can upload a PDF without errors
2. ✅ Document appears in the documents list
3. ✅ Search returns relevant text chunks
4. ✅ AI generates a response based on document content
5. ✅ You can delete documents

---

## 📞 Need Help?

If you encounter issues:
1. Check terminal outputs for error messages
2. Verify both servers are running
3. Ensure PDF is valid and not corrupted
4. Try refreshing the browser
5. Check browser console for JavaScript errors

**Server URLs:**
- Backend API: http://localhost:8000
- Frontend UI: http://localhost:5173
- API Docs: http://localhost:8000/docs (FastAPI auto-docs)

---

**Happy Testing! 🚀**
