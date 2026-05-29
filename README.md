# 🚀 NEXUS — Multi-Agent Data Analysis Platform

> **Deployment:** Work in progress — coming soon.

NEXUS is a **full-stack AI-powered data analysis platform** that automates the complete data science workflow — from raw CSV upload to cleaned datasets, statistical analysis, ML model training, and executive report generation — using a team of specialized AI agents.

---

# ✨ What NEXUS Does

Upload any CSV dataset and NEXUS automatically:

✅ Cleans and preprocesses the data

✅ Handles missing values, outliers, duplicates, and datatype corrections

✅ Runs multiple AI agents for deep analysis and insight generation

✅ Trains ML models automatically

✅ Generates downloadable PDF reports

✅ Lets users chat with their dataset using natural language

---

# 🧠 AI Workflow

```text
CSV Upload
    ↓
Cleaning Pipeline
(deduplication, imputation, outlier removal, type fixing)
    ↓
Celery Async Task Queue (Redis Broker)
    ↓
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  EDA Agent  │ →  │ Stats Agent │ →  │Insight Agent│
│ (structure) │    │(skew/kurt)  │    │ (synthesis) │
└─────────────┘    └─────────────┘    └─────────────┘
    ↓
ML Agent
(Random Forest + Logistic Regression)
    ↓
PDF Report Generation
    ↓
PostgreSQL Storage + Redis Cache
```

---

# ⚡ Features

## 🧹 Smart Cleaning Pipeline

* Automated 5-step data cleaning
* Missing value handling
* Duplicate removal
* Outlier detection
* Datatype correction
* Full cleaning audit log

---

## 🤖 Multi-Agent AI Analysis

Powered by **Groq LLaMA 3.3 70B** using:

* EDA Agent
* Statistical Analysis Agent
* Insight Generation Agent

Built with:

* LangChain
* LangGraph

---

## ⚙️ Async Task Processing

* Celery workers for background processing
* Redis broker integration
* Real-time progress polling
* Scalable task orchestration

---

## 📊 ML Auto-Training

Automatically:

* Detects classification vs regression problems
* Trains multiple ML models
* Returns:

  * Accuracy scores
  * Feature importance
  * Model comparisons

Models Used:

* Random Forest
* Logistic Regression

---

## 📄 PDF Report Generation

Generates complete multi-page reports containing:

* Dataset summary
* Statistical analysis
* Visual insights
* ML performance metrics
* AI-generated conclusions

---

## 💬 Dataset Chat Interface

Ask questions like:

* “What are the most important features?”
* “Show anomalies in sales”
* “Which columns have missing values?”

And receive:

* Natural language answers
* Chart recommendations
* Analytical insights

---

## 🗄️ Analysis History

* PostgreSQL persistence
* Redis result caching
* Historical analysis retrieval

---

## 🔐 Authentication & Security

* JWT Authentication
* Secure login/register flow
* Password hashing with bcrypt
* Protected API routes

---

## 🩺 Deep Health Monitoring

Live monitoring for:

* PostgreSQL connectivity
* Redis connectivity
* Groq API status
* Background workers

---

# 🛠️ Tech Stack

| Layer            | Technology                                   |
| ---------------- | -------------------------------------------- |
| Frontend         | React + Vite + Tailwind CSS + Recharts       |
| Backend          | FastAPI + Python                             |
| Database         | PostgreSQL + SQLAlchemy + Alembic            |
| Cache & Queue    | Redis + Celery + Flower                      |
| AI Agents        | LangChain + LangGraph + Groq (LLaMA 3.3 70B) |
| Authentication   | JWT (`python-jose` + `bcrypt`)               |
| Reports          | ReportLab PDF Generation                     |
| Machine Learning | scikit-learn                                 |
| Infrastructure   | Docker + Docker Compose                      |

---

# 🧱 System Architecture

```text
Frontend (React)
        ↓
FastAPI Backend
        ↓
Redis Queue + Celery Workers
        ↓
AI Multi-Agent Pipeline
        ↓
ML Training Layer
        ↓
PDF Report Generation
        ↓
PostgreSQL + Redis Cache
```

---

# 🚀 Running Locally

## 1️⃣ Clone the Repository

```bash
git clone https://github.com/Manya-kh10/NEXUS-Multi-Agent-Analysis-Platform.git

cd NEXUS-Multi-Agent-Analysis-Platform
```

---

## 2️⃣ Configure Environment Variables

```bash
cp .env.example .env
```

Fill in:

* `GROQ_API_KEY`
* PostgreSQL credentials
* `SECRET_KEY`

---

## 3️⃣ Start All Services

```bash
docker-compose up --build
```

---

# 🌐 Services

| Service           | URL                        |
| ----------------- | -------------------------- |
| FastAPI Backend   | http://localhost:8000      |
| API Documentation | http://localhost:8000/docs |
| Streamlit UI      | http://localhost:8501      |
| Flower Monitor    | http://localhost:5555      |

---

# 📡 API Endpoints

```http
POST   /api/auth/register
POST   /api/auth/login

POST   /api/pipeline/clean
GET    /api/pipeline/download/{filename}

POST   /api/tasks/analyze
GET    /api/tasks/status/{task_id}

POST   /api/ml/train

POST   /api/report/generate

POST   /api/chat/message

GET    /api/history/

GET    /api/health/
```

---

# 📈 Project Status

| Phase                                        | Status         |
| -------------------------------------------- | -------------- |
| Phase 1 — Infrastructure + Cleaning Pipeline | ✅ Complete     |
| Phase 2 — Multi-Agent Orchestration + Async  | ✅ Complete     |
| Phase 3 — ML Agent + PDF Reports + Auth      | ✅ Complete     |
| React Frontend                               | ✅ Complete     |
| Production Deployment (Vercel + Render)      | 🔄 In Progress |

---

# 🎯 Project Goals

This project demonstrates:

* Production-grade backend architecture
* Multi-agent LLM orchestration
* AI-powered analytics pipelines
* Async distributed processing
* ML automation workflows
* Full-stack AI engineering practices

---

# 📷 Future Improvements

* Real-time collaborative analysis
* Advanced visualization dashboard
* Additional ML models
* Vector database integration
* RAG-powered document analysis
* Role-based access control
* Kubernetes deployment

---

# 👨‍💻 Author

**Manya Khandelwal**

Built as a full-stack AI engineering project focused on scalable AI systems, agent orchestration, and automated analytics pipelines.

---

