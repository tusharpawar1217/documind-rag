# 🧪 DocuMind RAG - Complete Testing Guide

## 🎯 What to Test

This guide will help you verify that the RAG system is working correctly with **LLM synthesis** instead of raw chunks.

---

## 📋 Pre-Test Checklist

### ✅ **1. Servers Running**

```bash
# Backend (Terminal 1)
cd backend
python test_server.py
# Should see: ✅ Gemini LLM initialized

# Frontend (Terminal 2)
cd frontend
npm run dev
# Should see: Local: http://localhost:5173
```

### ✅ **2. Environment Variables**

Check `.env` file has:
```
GEMINI_API_KEY=AIzaSyAb8RN6JaiMaLSgl7oiw6ciVbZ9UH6MKkz-rKdZXYhedOC-BAJQ
```

---

## 🧪 Test Suite

### Test 1: Upload PDF Document

**Goal:** Verify chunking with semantic boundaries

**Steps:**
1. Go to http://localhost:5173/upload
2. Upload `thesis (1).pdf`
3. Wait for processing

**Expected Result:**
```
✅ Document uploaded successfully
✅ Extracted X pages and Y chunks
✅ No error messages
```

**Verify:**
- Upload completes without errors
- Chunk count is reasonable (not too many/few)
- Progress bar shows 100%

---

### Test 2: Search - Thesis Overview

**Goal:** Verify LLM synthesis vs raw chunks

**Steps:**
1. Go to http://localhost:5173/search
2. Enter query: `"What is this thesis about?"`
3. Click "Search"

**❌ BAD Result (Raw Chunks):**
```
Source 1: Phonetic... Reso... Technolog...
Source 2: AI-Generated and AI Voice Cloning Detection Using
Source 3: Tushar D. Pawar NaN undefined...
```

**✅ GOOD Result (LLM Synthesis):**
```
**Thesis Overview: AI-Generated & Voice Cloning Detection**

This M.Tech thesis, authored by **Tushar D. Pawar** (supervised by 
Dr. Vandana Dhingra), focuses on detecting AI-generated speech and 
voice deepfakes specifically for Indian languages like Marathi.

**Key Highlights:**

• Problem: Synthetic speech tools pose severe risks (scams, 
  disinformation). While detection models exist for English...
  
• Performance: The proposed deep learning model achieves 
  **98.77% accuracy** and an **Equal Error Rate (EER) of 0.91%**...

────────────────────────────────────────────────────────────
**📚 Sources**
────────────────────────────────────────────────────────────

📄 thesis.pdf - Pages 3, 5, 8
```

**Verify:**
- ✅ Answer is fluent and complete sentences
- ✅ No truncated text like "Phonetic... Reso..."
- ✅ Uses **bold** for emphasis
- ✅ Has bullet points (•)
- ✅ Page numbers at bottom, not in chunk headers
- ✅ NO "Source 1:", "Source 2:" headers

---

### Test 3: Search - Methodology Question

**Goal:** Verify structured answers

**Steps:**
1. Query: `"What methodologies are used?"`

**Expected Result:**
```
**Research Methodologies**

The thesis employs a **multi-stage deep learning approach** for 
detecting AI-generated voices in Indian languages:

**1. Data Collection & Preprocessing**
• Custom dataset creation for Marathi and Hindi
• Audio augmentation techniques
• Feature extraction using MFCCs

**2. Model Architecture**
• Convolutional Neural Networks (CNNs)
• Bidirectional LSTM layers
• Attention mechanisms

(and so on...)

────────────────────────────────────────────────────────────
**📚 Sources**
────────────────────────────────────────────────────────────

📄 thesis.pdf - Pages 12, 18, 22
```

**Verify:**
- ✅ Structured with headers
- ✅ Numbered lists
- ✅ Bullet points
- ✅ Complete sentences
- ✅ Bold emphasis on key terms

---

### Test 4: Search - Performance Metrics

**Goal:** Verify factual accuracy extraction

**Steps:**
1. Query: `"What is the model accuracy?"`

**Expected Result:**
```
**Model Performance**

The proposed model demonstrates **excellent accuracy** on the 
Marathi test set:

• Overall Accuracy: 98.77%
• Equal Error Rate (EER): 0.91%
• F1-Score: 98.5%

────────────────────────────────────────────────────────────
**📚 Sources**
────────────────────────────────────────────────────────────

📄 thesis.pdf - Pages 28, 31
```

**Verify:**
- ✅ Specific numbers extracted correctly
- ✅ NOT showing raw chunks with numbers cut off
- ✅ Professional formatting

---

### Test 5: Chat Interface

**Goal:** Verify conversational RAG

**Steps:**
1. Go to http://localhost:5173/chat
2. Ask: `"Tell me about this thesis"`
3. Follow-up: `"What datasets were used?"`
4. Follow-up: `"How accurate is it?"`

**Expected Results:**

**Message 1:**
```
This thesis focuses on AI-generated voice detection for Indian 
languages like Marathi. The research uses deep learning to...
```

**Message 2:**
```
The research used both existing and custom datasets:

• ASVspoof 2019 (English baseline)
• Custom Marathi Voice Dataset: 5,000+ samples
  - Real: 2,500 recordings...
```

**Message 3:**
```
The model achieves **98.77% accuracy** with an Equal Error Rate 
(EER) of **0.91%** on the Marathi test set...
```

**Verify:**
- ✅ Conversations flow naturally
- ✅ Follow-up questions work
- ✅ History preserved (scroll up to see old messages)
- ✅ Typing indicator shows while generating
- ✅ Responses formatted with bold, bullets

---

### Test 6: Chat History Persistence

**Goal:** Verify history saves and loads

**Steps:**
1. Have a conversation (3-4 messages)
2. Click "Clear History" button
3. Confirm it clears
4. Ask new question
5. Refresh browser page
6. Check if messages reappear

**Expected:**
- ✅ Clear History removes all messages
- ✅ New conversation starts fresh
- ✅ Messages persist after refresh

---

### Test 7: Source Citations

**Goal:** Verify page number accuracy

**Steps:**
1. Search for something specific: `"What page mentions accuracy results?"`
2. Check the response
3. Manually open the PDF
4. Verify page numbers match

**Expected:**
- ✅ Page numbers are accurate
- ✅ Citations at bottom of response
- ✅ Format: `📄 filename.pdf - Pages X, Y, Z`

---

### Test 8: Empty/Invalid Queries

**Goal:** Verify error handling

**Steps:**
1. Search with empty query
2. Search for something not in document: `"What is quantum mechanics?"`

**Expected:**

**Empty Query:**
```
❌ "Please enter a search query" toast
```

**Not Found:**
```
**No results found for:** quantum mechanics

**Suggestions:**
• Try different keywords
• Use more specific terms
• Check if your documents contain this information
```

**Verify:**
- ✅ Handles gracefully
- ✅ Provides helpful suggestions
- ✅ No crashes or errors

---

### Test 9: Multiple Documents

**Goal:** Verify multi-document search

**Steps:**
1. Upload 2-3 different PDFs
2. Search for something that appears in multiple docs
3. Check results

**Expected:**
```
**Answer synthesized from multiple documents**

────────────────────────────────────────────────────────────
**📚 Sources**
────────────────────────────────────────────────────────────

📄 doc1.pdf - Pages 3, 5
📄 doc2.pdf - Page 7
```

**Verify:**
- ✅ Can search across documents
- ✅ Citations show multiple files
- ✅ Answer combines info from both

---

### Test 10: UI Formatting

**Goal:** Verify rich text rendering

**Steps:**
1. Search for any query
2. Inspect the response visually

**Check for:**
- ✅ **Bold text** renders correctly
- ✅ Bullet points (•) are indented
- ✅ Numbered lists (1., 2., 3.) show
- ✅ Separators (─────) display as lines
- ✅ Emojis (📚 📄 💡) appear
- ✅ Paragraphs have proper spacing
- ✅ Text is readable (not overlapping)

---

## 🎨 Visual Quality Checks

### Response Card
- ✅ Purple gradient background
- ✅ Sparkles icon (✨)
- ✅ "AI Response" header
- ✅ Readable text (white, not too faint)
- ✅ Proper padding and margins

### Source Citations
- ✅ Clear separation from answer
- ✅ Source section at bottom
- ✅ Page numbers clearly visible
- ✅ Document emoji (📄)

### Chat Messages
- ✅ User messages: right-aligned, purple
- ✅ AI messages: left-aligned, dark background
- ✅ Typing indicator: animated dots
- ✅ Timestamps visible

---

## 🐛 Common Issues & Fixes

### Issue 1: Seeing Raw Chunks
**Symptom:**
```
Source 1: Phonetic... Reso...
```

**Fix:**
- Check Gemini API key is set
- Restart backend server
- Look for "✅ Gemini LLM initialized" message

### Issue 2: Truncated Text
**Symptom:**
```
The thesis descr...
```

**Fix:**
- Already fixed with semantic chunking
- If still happening, check chunk size (should be 800 chars)

### Issue 3: No Bold/Bullets
**Symptom:**
- Everything is plain text
- **Bold** shows as **text** literally

**Fix:**
- Frontend formatting is working
- Check if response contains `**` markers
- Refresh browser (Ctrl+F5)

### Issue 4: LLM Not Responding
**Symptom:**
```
Failed to get response
```

**Fix:**
- Check internet connection
- Verify Gemini API key is valid
- Check backend logs for errors
- Fallback response should still show

---

## 📊 Success Criteria

Your RAG system is working correctly if:

✅ **1. No Raw Chunks**
- Responses are fluent sentences, NOT "Source 1: ..."

✅ **2. Complete Sentences**
- No truncated text like "Phonetic... Reso..."

✅ **3. Rich Formatting**
- Bold text works
- Bullet points display
- Structure is clear

✅ **4. Accurate Citations**
- Page numbers are correct
- Citations at bottom, not inline

✅ **5. Professional Tone**
- Reads like a knowledgeable assistant
- Not robotic or fragmented

✅ **6. Chat Works**
- Conversations flow naturally
- History persists
- Follow-ups understand context

---

## 🎯 Quick Smoke Test (2 minutes)

1. **Upload** thesis PDF ✅
2. **Search**: "What is this about?" ✅
3. **Verify**: 
   - Fluent answer? ✅
   - Bold text? ✅
   - Page numbers at bottom? ✅
4. **Chat**: Ask follow-up ✅
5. **Check**: Formatted correctly? ✅

**If all ✅ → System is working!**

---

## 📝 Test Results Template

Copy this for your test report:

```
# Test Results - [Date]

## Test 1: Upload PDF
Status: ✅ / ❌
Notes:

## Test 2: Search Overview
Status: ✅ / ❌
Response Quality: [Raw Chunks / Synthesized]
Notes:

## Test 3: Methodology
Status: ✅ / ❌
Formatting: [Bold: Y/N, Bullets: Y/N]
Notes:

## Test 4: Performance
Status: ✅ / ❌
Numbers Accurate: Y/N
Notes:

## Test 5: Chat
Status: ✅ / ❌
Follow-ups Work: Y/N
Notes:

## Overall: ✅ PASS / ❌ FAIL
```

---

## 🚀 Performance Expectations

**Response Times:**
- Upload (10-page PDF): ~5-10 seconds
- Search query: ~2-4 seconds
- Chat message: ~2-4 seconds

**Accuracy:**
- Page citations: 100% accurate
- Synthesis quality: Professional, fluent
- Formatting: Rich text renders correctly

---

## 📞 Troubleshooting

**Still seeing issues?**

1. Check backend logs:
   ```bash
   # Look for errors in terminal running test_server.py
   ```

2. Check browser console:
   ```bash
   # Press F12 → Console tab → Look for errors
   ```

3. Verify API calls:
   ```bash
   # Network tab → Check /api/v1/search/query response
   ```

4. Test direct API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/search/query \
     -H "Content-Type: application/json" \
     -d '{"query":"test","top_k":3}'
   ```

---

**Last Updated:** 2026-08-03  
**Version:** 2.0  
**Status:** ✅ Ready for Testing
