````md
# 🎯 AI Exam Mentor

An AI-powered learning assistant built for **Government Exam Aspirants** that transforms long educational videos and current affairs content into **smart summaries, quizzes, and contextual doubt solving** using **Generative AI, RAG, embeddings, and LLM workflows**.

Designed to reduce **information overload** and help students learn smarter from long-form educational content.

---

## 🌐 Live Demo

**Deployed Website:**  
(https://ai-teacher-afu6.onrender.com)

---

## 🚀 Features

### 📺 Educational Video Learning
- Upload educational videos directly
- Add educational YouTube videos
- Automatic video transcription

### 💬 AI Contextual Doubt Solving
- Ask questions directly from uploaded educational content
- Context-aware responses using **Retrieval-Augmented Generation (RAG)**

### 📖 Smart Summaries
Generate concise educational summaries from long videos instantly.

### 📝 Personalized Quiz Generation
AI-generated quizzes tailored to:

- UPSC
- APSC
- SSC
- Banking
- Railway
- ADRE

### 🎯 Exam Profile Based Learning
The system personalizes:
- AI summaries
- Revision flow
- Quiz difficulty
- Question style

based on the selected government exam profile.

### 📰 Current Affairs Friendly
Ideal for:
- Current Affairs videos
- Educational lectures
- Government exam preparation content

---

## 🧠 Tech Stack

### Backend
- FastAPI
- Python

### Generative AI
- OpenAI Embeddings
- Groq LLM API
- RAG (Retrieval-Augmented Generation)
- Semantic Search
- FAISS Vector Retrieval

### Frontend
- HTML
- CSS
- JavaScript

### Deployment
- Render
- ngrok (for transcript service)

---

## ⚙️ How The System Works

```text
                ┌──────────────────────────┐
                │   Start FastAPI Server   │
                │   (uvicorn app:app)      │
                └────────────┬─────────────┘
                             │
                             ▼
        ┌──────────────────────────────────────┐
        │ Import all modules (startup phase)   │
        └────────────────┬────────────────────┘
                         │
                         ▼
                ┌───────────────────┐
                │   Wait for user   │
                │     request       │
                └────────┬──────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼

┌───────────────────────┐      ┌────────────────────────┐
│ 🎥 Upload Video API   │      │ 💬 Chat API (/chat)    │
│     (/upload)         │      └────────────┬───────────┘
└──────────┬────────────┘                   │
           ▼                                ▼
┌────────────────────────────┐    ┌────────────────────────────┐
│ Convert video → audio      │    │ Check question type        │
└──────────┬─────────────────┘    │ is_video_question(query)   │
           ▼                      └────────────┬───────────────┘
┌────────────────────────────┐                 │
│ Transcribe audio           │                 │
└──────────┬─────────────────┘                 │
           ▼                                   │
┌────────────────────────────┐                 │
│ Create chunks              │                 │
└──────────┬─────────────────┘                 │
           ▼                                   │
┌────────────────────────────┐                 │
│ Store in GLOBAL_CHUNKS     │◄────────────────┘
└──────────┬─────────────────┘
           ▼
┌────────────────────────────┐
│ Create embeddings (FAISS)  │
└──────────┬─────────────────┘
           ▼
      ✅ Video processed
````

---

## 🔀 Chat Flow (RAG Decision System)

The system first checks whether the question is related to uploaded study material.

### Video Question → Uses RAG

```text
User Question
      ↓
is_video_question(query)
      ↓
TRUE
      ↓
Retrieve relevant chunks
      ↓
Semantic search (FAISS)
      ↓
Context generation
      ↓
LLM Answer
```

### Normal Question → Direct LLM

```text
User Question
      ↓
FALSE
      ↓
Skip retrieval
      ↓
Direct LLM response
```

---

## ⚠️ Important Note

This application **does not include preloaded study material**.

To use the app:

1. Upload a video file **OR**
2. Add a YouTube educational video

The system will automatically:

* Transcribe content
* Create chunks
* Generate embeddings
* Enable contextual AI learning

Without uploading educational content, only general AI responses are available.

---

# 🔐 Environment Variables

This project uses secret API keys.

Create a `.env` file in the root directory.

Example:

```env
OPENAI_API_KEY=your_openai_api_key
GROQ_API_KEY=your_groq_api_key
TRANSCRIPT_SERVICE_URL=https://your-ngrok-url.ngrok-free.app
```

### Variable Explanation

| Variable                 | Purpose                                     |
| ------------------------ | ------------------------------------------- |
| `OPENAI_API_KEY`         | Used for embeddings generation              |
| `GROQ_API_KEY`           | Used for LLM responses + transcription      |
| `TRANSCRIPT_SERVICE_URL` | Used only for YouTube transcript extraction |

---

## ⚠️ Why `TRANSCRIPT_SERVICE_URL` Exists

**YouTube uploads require a local transcript service.**

To avoid YouTube transcript blocking issues, the transcript system runs separately on the developer's local machine and is exposed through **ngrok**.

This means:

### ✅ Normal Video Uploads

Work directly through deployment.

### ⚠️ YouTube Uploads

Require the transcript mini-server to be running.

If you want to test YouTube uploads, please contact the repository owner.

---

## 🛠️ Local Setup

Clone repository:

```bash
git clone https://github.com/your-username/AI-teacher.git
```

Move into project:

```bash
cd AI-teacher
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` file:

```env
OPENAI_API_KEY=your_key
GROQ_API_KEY=your_key
TRANSCRIPT_SERVICE_URL=your_url
```

Run server:

```bash
uvicorn app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

---

## 🚀 Render Deployment

This project is deployed using **Render**.

Add the following Environment Variables in Render:

```text
OPENAI_API_KEY
GROQ_API_KEY
TRANSCRIPT_SERVICE_URL
```

Go to:

```text
Render Dashboard
→ Service
→ Environment Variables
```

Then redeploy the application.

---

## 📈 Future Improvements

Planned upgrades include:

* Persistent user sessions
* Multi-user support
* Smarter contextual memory
* Improved UI/UX
* Better YouTube handling
* Personalized revision tracking
* AI voice interaction
* Advanced analytics dashboard
* Multi-language learning support

This project is actively being improved.

---

## 🤝 Contributing

Contributions are welcome.

Before contributing:

1. Setup `.env`
2. Add required API keys
3. Ensure transcript service is configured

For YouTube transcript testing, contact the repository owner.

---

## 📄 License

This project is licensed under the **GNU GPL v3 License**.

See the `LICENSE` file for details.

---

## 👨‍💻 Author

**Ankuran Khanikar**

Aspiring **Generative AI Engineer** building practical AI products using:

* RAG
* LLMs
* FastAPI
* OpenAI
* Applied AI Systems

```
```
