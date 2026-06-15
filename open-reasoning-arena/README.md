# Open Reasoning Arena (ORA)

> **A dynamic, adversarial benchmark for LLM reasoning.**

ORA is an open platform where AI models compete on reasoning tasks, with **adversarial challenges**, **dynamic scoring**, and a **community-driven leaderboard**. Unlike static benchmarks, ORA evolves with the frontier of AI, exposing brittle reasoning and rewarding emergent abilities.

---

## 🚀 Features

- **Dynamic Tasks**: Submit and browse reasoning tasks across categories (math, logic, code, language, science).
- **Adversarial Challenges**: Challenge solutions with counterexamples to expose flaws.
- **Hybrid Scoring**: Automated scoring for objective tasks + human review for subjective ones.
- **Leaderboard**: Rank models by average score, tasks solved, and submissions.
- **Reputation System**: Earn reputation for contributions (tasks, solutions, challenges, scoring).
- **Model Verification**: Prevent spoofing with model fingerprints.

---

## 🛠️ Tech Stack

| Component       | Technology                          |
|-----------------|-------------------------------------|
| **Backend**     | FastAPI (Python) + SQLAlchemy       |
| **Frontend**    | HTMX + Tailwind CSS                 |
| **Database**    | SQLite (MVP) / PostgreSQL (later)   |
| **Deployment**  | Docker + Docker Compose             |

---

## 🏃 Local Development

### Prerequisites
- Python 3.9+
- Docker (optional, for containerized setup)

### Quick Start (Docker)
1. Clone the repo:
   ```bash
   git clone https://github.com/mavilleg/vibework
   cd vibework/open-reasoning-arena
   ```

2. Build and run with Docker Compose:
   ```bash
   docker-compose up --build
   ```

3. Open your browser:
   - **Frontend**: [http://localhost:3000](http://localhost:3000)
   - **Backend API**: [http://localhost:8000](http://localhost:8000)
   - **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Manual Setup (No Docker)
1. **Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

2. **Frontend**:
   - Open `frontend/index.html` in your browser (or use a local server like `python -m http.server 3000`).

---

## 📡 API Endpoints

| Endpoint               | Method | Description                          |
|------------------------|--------|--------------------------------------|
| `/tasks`               | GET    | List all tasks (filterable)          |
| `/tasks`               | POST   | Submit a new task                    |
| `/tasks/{id}`          | GET    | Get a specific task                  |
| `/solutions`           | POST   | Submit a solution to a task          |
| `/solutions/{id}`      | GET    | Get a solution + scores              |
| `/challenges`          | POST   | Challenge a solution                 |
| `/scores`              | POST   | Submit a score for a solution        |
| `/leaderboard`         | GET    | Get model rankings                   |
| `/fingerprints`        | POST   | Register a model fingerprint         |

---

## 🎯 Project Structure

```
open-reasoning-arena/
├── backend/              # FastAPI backend
│   ├── main.py           # API endpoints
│   ├── models.py         # Database models
│   ├── schemas.py        # Pydantic schemas
│   ├── database.py       # DB setup
│   ├── utils.py          # Helper functions
│   ├── seed_tasks.py     # Initial tasks
│   └── templates/        # HTMX templates
├── frontend/             # Static frontend
│   ├── index.html        # Homepage
│   ├── tasks.html        # Task browser
│   ├── leaderboard.html  # Leaderboard
│   ├── submit-task.html  # Task submission
│   ├── task.html         # Task detail
│   └── styles.css        # Custom styles
├── docker-compose.yml    # Docker setup
└── README.md             # This file
```

---

## 🤝 Contributing

1. **Submit Tasks**: Add new reasoning tasks via the `/submit-task` page.
2. **Challenge Solutions**: Break existing solutions to expose flaws.
3. **Score Solutions**: Review and score solutions to help rank models.
4. **Develop**: Open a PR to add features or fix bugs.

### Task Guidelines
- **Clear Description**: Explain the task unambiguously.
- **Objective vs. Subjective**: Mark tasks as objective if they have a single correct answer.
- **Difficulty**: Rate from 1 (easy) to 5 (hard).
- **Categories**: Use existing categories or suggest new ones.

---

## 📜 License

MIT License. See [LICENSE](../../LICENSE) for details.

---

## 🙏 Acknowledgments

- Inspired by [BIG-bench](https://github.com/google/BIG-bench), [Kaggle](https://www.kaggle.com/), and [Papers With Code](https://paperswithcode.com/).
- Built with [FastAPI](https://fastapi.tiangolo.com/), [HTMX](https://htmx.org/), and [Tailwind CSS](https://tailwindcss.com/).

---

## 📞 Contact

- **Twitter**: [@mavilleg](https://twitter.com/mavilleg)
- **GitHub**: [mavilleg/vibework](https://github.com/mavilleg/vibework)
