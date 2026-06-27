# Personal ATS - Applicant Tracking System

## Overview

Personal ATS is an intelligent Applicant Tracking System (ATS) designed to streamline recruitment workflows. It provides job posting management, application tracking, candidate evaluation, and intelligent recommendations powered by data analytics.

## Key Features

- 📋 **Job Management**: Create and manage job postings
- 📨 **Application Tracking**: Track candidates through the pipeline
- 🔍 **Smart Filtering**: Intelligent candidate filtering and ranking
- 📊 **Analytics Dashboard**: Real-time recruitment metrics
- 🎯 **Quality Scoring**: Candidate quality assessment
- 📧 **Email Integration**: Automated candidate communication
- 🔗 **URL Validation**: Verify candidate links and portfolios
- 📝 **Markdown Support**: Rich text processing for job descriptions
- 🚀 **Automated Pipeline**: Daily job processing and recommendations
- 🔐 **Secure**: JWT-based authentication

## Architecture

```
┌─────────────────────────────────────┐
│    Frontend Dashboard               │
│    (Job Posting, Candidate View)    │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│    ATS API Backend (Python)         │
│    - Job Management                 │
│    - Application Processing         │
│    - Candidate Scoring              │
└─────────────┬───────────────────────┘
              │
      ┌───────┴────────────┬────────────┐
      ▼                    ▼            ▼
   Database          Cache Layer    Task Queue
  (PostgreSQL)       (Redis)       (Celery)
      │                   │            │
      ├─ Jobs            ├─ Scores    ├─ Daily Jobs
      ├─ Candidates      ├─ Sessions  ├─ Email
      ├─ Applications    └─ Temp      └─ Reports
      └─ Analytics
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11, Flask/FastAPI |
| Database | PostgreSQL 13+ |
| Cache | Redis |
| Task Queue | Celery |
| Frontend | React/Vue.js |
| API Docs | Swagger/OpenAPI |
| Testing | pytest |
| Deployment | Docker, Kubernetes |

## Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Redis 7+
- Docker & Docker Compose (recommended)
- Node.js 18+ (for frontend)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/BODAPATI88/personal-ats.git
cd personal-ats
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
vim .env
```

### 3. Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 4. Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask db upgrade

# Run development server
flask run
```

### 5. Access the Application

- API: http://localhost:5000
- Frontend: http://localhost:3000
- API Docs: http://localhost:5000/api/docs

## Project Structure

```
personal-ats/
├── README.md
├── requirements.txt
├── .gitignore
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── app.py                   # Flask app entry
│   ├── config.py                # Configuration
│   ├── version.py               # Version info
│   │
│   ├── models/
│   │   ├── job.py              # Job model
│   │   ├── candidate.py         # Candidate model
│   │   ├── application.py       # Application model
│   │   └── analytics.py         # Analytics model
│   │
│   ├── routes/
│   │   ├── jobs.py             # Job endpoints
│   │   ├── candidates.py        # Candidate endpoints
│   │   ├── applications.py      # Application endpoints
│   │   └── analytics.py         # Analytics endpoints
│   │
│   ├── services/
│   │   ├── job_service.py       # Job business logic
│   │   ├── candidate_service.py # Candidate logic
│   │   ├── scoring_service.py   # Quality scoring
│   │   ├── email_service.py     # Email sending
│   │   └── cache_service.py     # Caching
│   │
│   ├── jobs/
│   │   ├── run_daily_jobs.sh    # Daily pipeline
│   │   ├── import_jobs.py       # Job import
│   │   ├── validate_job_urls.py # URL validation
│   │   ├── score_jobs.py        # Job scoring
│   │   └── recommend.py         # Recommendations
│   │
│   ├── utils/
│   │   ├── validators.py        # Input validation
│   │   ├── decorators.py        # Auth decorators
│   │   ├── sanitize.py          # Data sanitization
│   │   └── helpers.py           # Helper functions
│   │
│   └── tests/
│       ├── test_jobs.py
│       ├── test_candidates.py
│       └── test_scoring.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   └── package.json
│
├── docs/
│   ├── API.md                   # API documentation
│   ├── ARCHITECTURE.md          # Architecture details
│   └── DEPLOYMENT.md            # Deployment guide
│
└── scripts/
    ├── seed_data.py             # Initial data
    └── cleanup.py               # Database cleanup
```

## API Documentation

### Authentication

```bash
# Login
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "password"
}

Response:
{
  "token": "eyJhbGc...",
  "expires_in": 3600
}
```

### Job Management

```bash
# Create job posting
POST /api/jobs
Authorization: Bearer <token>
{
  "title": "Senior Python Developer",
  "description": "...",
  "location": "Remote",
  "salary_min": 80000,
  "salary_max": 120000
}

# Get all jobs
GET /api/jobs

# Get specific job
GET /api/jobs/{job_id}

# Update job
PUT /api/jobs/{job_id}

# Delete job
DELETE /api/jobs/{job_id}
```

### Candidate Management

```bash
# Submit application
POST /api/candidates/apply
{
  "job_id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "resume_url": "https://example.com/resume.pdf",
  "portfolio_url": "https://johndoe.dev"
}

# Get candidates for job
GET /api/jobs/{job_id}/candidates

# Get candidate details
GET /api/candidates/{candidate_id}

# Update candidate status
PUT /api/candidates/{candidate_id}
{
  "status": "interviewed"
}
```

### Analytics

```bash
# Get dashboard metrics
GET /api/analytics/dashboard

Response:
{
  "total_jobs": 15,
  "total_applications": 342,
  "active_jobs": 8,
  "quality_score": 78.5,
  "conversion_rate": 12.3,
  "time_to_hire": 24.5
}
```

See [docs/API.md](docs/API.md) for complete API reference.

## Daily Pipeline

The system runs an automated daily pipeline:

```bash
# Daily Job Processing Pipeline (cron: 0 2 * * *)
1. Import new job postings
2. Validate candidate URLs
3. Score all candidates
4. Generate recommendations
5. Send email notifications
6. Generate reports
```

Run manually:
```bash
bash jobs/run_daily_jobs.sh
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `FLASK_ENV` | Environment | development |
| `DATABASE_URL` | PostgreSQL URI | (required) |
| `REDIS_URL` | Redis URI | redis://localhost |
| `JWT_SECRET` | JWT secret key | (required) |
| `SMTP_HOST` | Email server | smtp.gmail.com |
| `SMTP_USER` | Email username | (required) |
| `SMTP_PASSWORD` | Email password | (required) |

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend

# Run specific test
pytest tests/test_scoring.py::test_quality_score
```

### Code Quality

```bash
# Format code
black backend/

# Lint
flake8 backend/

# Type checking
mypy backend/
```

### Database Migrations

```bash
# Create migration
flask db migrate -m "Add new column"

# Apply migration
flask db upgrade

# Rollback
flask db downgrade
```

## Production Deployment

### Using Kubernetes

```bash
# Build image
docker build -t ats:latest .

# Push to registry
docker tag ats:latest myregistry/ats:latest
docker push myregistry/ats:latest

# Deploy
kubectl apply -f k8s/deployment.yaml
```

### Using Docker Compose

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

## Troubleshooting

### Database Connection Issues

```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check migrations
flask db current
flask db history
```

### Redis Connection Issues

```bash
# Test Redis
redis-cli ping

# Check Redis info
redis-cli info
```

### URL Validation Issues

```bash
# Run validation manually
python backend/jobs/validate_job_urls.py

# View logs
grep "validation" /var/log/ats.log
```

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more solutions.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check documentation in `docs/`
- Email: support@personalats.io

## Roadmap

- [ ] Mobile app (iOS/Android)
- [ ] AI-powered interview scheduling
- [ ] Resume parsing with ML
- [ ] Integration with job boards (LinkedIn, Indeed)
- [ ] Video interview support
- [ ] Offer generation and e-signing
- [ ] Reporting and analytics improvements
