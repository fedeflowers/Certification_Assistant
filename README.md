# Certification Assistant - Modernized Architecture

A modern web application to help study for IT certification exams by extracting questions from PDFs and providing an interactive quiz experience.

## 🏗️ Architecture

This application has been modernized from a Streamlit-based monolith to a modern React/FastAPI architecture:

```
┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│    Backend      │
│   (Next.js 14)  │     │   (FastAPI)     │
│   Port: 3000    │     │   Port: 8000    │
└─────────────────┘     └─────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
     ┌──────────┐      ┌──────────┐      ┌──────────┐
     │PostgreSQL│      │  Redis   │      │  File    │
     │   :5432  │      │  :6379   │      │ Storage  │
     └──────────┘      └──────────┘      └──────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API Key or Google Gemini API Key

### Running the Application

1. **Clone the repository**

2. **Set up environment variables**
   ```bash
   export OPENAI_API_KEY=your-openai-key
   # or
   export GEMINI_API_KEY=your-gemini-key
   ```

3. **Start all services**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## 📁 Project Structure

```
.
├── docker-compose.yml      # Multi-container orchestration
├── backend/                # FastAPI backend
│   ├── main.py            # Application entry point
│   ├── shared/            # Shared modules
│   │   ├── config.py      # Configuration
│   │   ├── database.py    # Database connection
│   │   ├── cache.py       # Redis cache
│   │   ├── models.py      # SQLAlchemy models
│   │   └── dependencies.py # FastAPI dependencies
│   ├── certifications/    # Certification feature
│   │   ├── routes.py      # API endpoints
│   │   ├── services.py    # Business logic
│   │   ├── tasks.py       # Background PDF processing
│   │   └── schemas.py     # Pydantic schemas
│   ├── quiz/              # Quiz feature
│   │   ├── routes.py
│   │   ├── services.py
│   │   └── schemas.py
│   └── analytics/         # Analytics feature
│       ├── routes.py
│       ├── services.py
│       └── schemas.py
└── frontend/              # Next.js frontend
    ├── app/               # App Router pages
    │   ├── page.tsx       # Dashboard
    │   ├── quiz/          # Quiz pages
    │   ├── analytics/     # Analytics page
    │   ├── library/       # Library page
    │   └── bookmarks/     # Bookmarks page
    ├── components/        # React components
    ├── contexts/          # React Context providers
    ├── lib/               # Utilities & API client
    └── types/             # TypeScript types
```

## 🔧 Backend API Endpoints

### Certifications
- `POST /certifications/upload` - Upload PDF
- `GET /certifications/` - List all certifications
- `GET /certifications/{id}` - Get certification details
- `GET /certifications/{id}/status` - Get processing status
- `DELETE /certifications/{id}` - Delete certification

### Quiz
- `GET /quiz/suggestions/{certification_id}` - Get smart quiz suggestions
- `POST /quiz/sessions` - Start new quiz session
- `GET /quiz/sessions/{id}` - Get session details
- `POST /quiz/sessions/{id}/answer` - Submit answer
- `PUT /quiz/sessions/{id}/end` - End session
- `GET /quiz/sessions/{id}/results` - Get session results

### Bookmarks
- `GET /bookmarks/{certification_id}` - List bookmarks
- `POST /bookmarks/` - Add bookmark
- `DELETE /bookmarks/{question_id}` - Remove bookmark

### Analytics
- `GET /analytics/{certification_id}/stats` - Overall statistics
- `GET /analytics/{certification_id}/weak-areas` - Weak areas
- `GET /analytics/{certification_id}/progress` - Progress trend

## 🗃️ Database Schema

| Table | Description |
|-------|-------------|
| `certifications` | Uploaded PDFs and metadata |
| `questions` | Extracted questions |
| `question_images` | Images associated with questions |
| `quiz_sessions` | Quiz session records |
| `session_answers` | Individual question answers |
| `bookmarked_questions` | User bookmarks |
| `analytics_cache` | Cached analytics data |

## ⚡ Key Features

- **PDF Processing**: Extract questions and images from certification PDFs using pdfplumber and pdf2image
- **LLM Parsing**: Use OpenAI or Gemini to parse question blocks into structured data
- **Smart Suggestions**: Get quiz recommendations based on weak areas, unseen questions, and mistakes
- **Real-time Progress**: Track processing status with polling
- **Analytics Dashboard**: View accuracy, study streaks, weak areas, and exam readiness
- **Bookmarks**: Save questions for later review
- **Image Support**: Display images embedded in questions

## 🔄 Development

### Backend Development
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

## 📝 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key | One of these |
| `GEMINI_API_KEY` | Google Gemini API key | One of these |
| `PDF_STORAGE_PATH` | Path to store PDFs | No (default: /app/pdfs) |

## 📜 License

MIT License
