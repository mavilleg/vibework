# 📚 Library of Babel

> *"The universe (which others call the Library) is composed of an indefinite and perhaps infinite number of hexagonal galleries..."* - Jorge Luis Borges

[![Azure Deploy](https://img.shields.io/badge/Deploy%20to%20Azure-0078D4?style=for-the-badge&logo=microsoft-azure&logoColor=white)](https://portal.azure.com/)
[![GitHub Actions](https://github.com/mavilleg/vibework/actions/workflows/azure-deploy.yml/badge.svg)](https://github.com/mavilleg/vibework/actions/workflows/azure-deploy.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

## 🌌 Overview

The Library of Babel is a digital implementation of Jorge Luis Borges' famous short story. This project provides a system to explore the mathematical concept of a library containing all possible books of a given format.

**Key Statistics:**
- **Total Possible Books**: 25^1,312,000 ≈ 10^1,834,100 (more than atoms in the observable universe)
- **Book Format**: 410 pages × 40 lines × ~80 characters
- **Character Set**: 25 characters (22 letters + space + comma + period)

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Azure CLI (for deployment)
- GitHub account with Azure integration

### Local Development
```bash
# Clone the repository
git clone https://github.com/mavilleg/vibework.git
cd vibework/library-of-babel

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the development server
python -m src.main

# Access the API at http://localhost:8000
```

### Docker Development
```bash
# Build the image
docker build -t library-of-babel .

# Run the container
docker run -p 8000:8000 library-of-babel
```

## 🏗️ Architecture

### Cost-Effective Azure Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Azure Cloud Infrastructure                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │   Frontend   │    │    API       │    │   Book Generation    │  │
│  │  (Static)    │───▶│  (App Service)│───▶│   (Serverless)       │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│           ▲                  ▲  ▲  ▲                  ▲              │
│           │                  │  │  │                  │              │
│  ┌─────────────┐    ┌─────┴──┴──┴─────┐    ┌─────────────────┐  │
│  │   CDN       │    │   Azure Cache  │    │   Blob Storage    │  │
│  │  (Static)    │    │   (Redis)      │    │   (Cold Storage)  │  │
│  └─────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Cost Optimization Strategies

1. **Serverless Computing**: Use Azure Functions for book generation (pay-per-use)
2. **Cold Storage**: Azure Blob Storage for archival (cheapest tier)
3. **Caching**: Azure Cache for Redis to cache frequently accessed books
4. **Static Hosting**: Azure Static Web Apps for frontend (free tier available)
5. **Auto-scaling**: Azure App Service with consumption plan
6. **CDN**: Azure CDN for static assets (reduces bandwidth costs)

### Estimated Monthly Costs

| Service | Tier | Estimated Cost | Notes |
|---------|------|----------------|-------|
| App Service | Free | $0 | For development |
| App Service | Basic | $13-55/month | Production |
| Functions | Consumption | $0-10/month | Pay per execution |
| Blob Storage | Cool | $0.01/GB/month | For cached books |
| Redis Cache | Basic | $15-75/month | Caching layer |
| CDN | Standard | $0.087/GB | Outbound data |

**Total Estimated**: $15-150/month depending on usage

## 🔧 Azure Deployment

### Option 1: GitHub Actions (Recommended)

This repository includes a GitHub Actions workflow at `.github/workflows/azure-deploy.yml` for automatic deployment to Azure App Service.

1. **Create Azure resources once**
   - Create an Azure App Service for Containers
   - Create or choose an Azure Container Registry (ACR)
   - Note the App Service name, resource group, and ACR login server

2. **Enable Azure integration in GitHub**
   - Go to your GitHub repository Settings
   - Navigate to **Secrets and variables** > **Actions**
   - Add the following secrets:
     - `AZURE_CREDENTIALS`: JSON output from `az ad sp create-for-rbac`
     - `AZURE_APP_SERVICE_NAME`: Your Azure Web App name
     - `AZURE_RESOURCE_GROUP`: Your Azure resource group
     - `REGISTRY_LOGIN_SERVER`: Your ACR login server (for example `example.azurecr.io`)
     - `REGISTRY_USERNAME`: Your ACR username
     - `REGISTRY_PASSWORD`: Your ACR password

3. **Deploy**
   - Push changes to `main`, or run the **Deploy to Azure** workflow manually from the Actions tab
   - GitHub Actions will test the app, build the container from `library-of-babel`, push it to ACR, and update the Azure Web App container

### Option 2: Manual Deployment via Azure CLI

1. **Create Resources**
```bash
# Login to Azure
az login

# Create resource group
az group create --name babel-library-rg --location eastus

# Create App Service plan and Linux web app
az appservice plan create --name babel-library-plan \
  --resource-group babel-library-rg \
  --is-linux --sku B1

az webapp create --resource-group babel-library-rg \
  --plan babel-library-plan \
  --name babel-library-api \
  --deployment-container-image-name nginx

# Create Azure Container Registry
az acr create --resource-group babel-library-rg \
  --name babellibraryacr \
  --sku Basic

# Create Storage Account
az storage account create --resource-group babel-library-rg \
  --name babellibrarystorage \
  --sku Standard_LRS \
  --encryption-services blob

# Create Redis Cache
az redis create --resource-group babel-library-rg \
  --name babel-library-cache \
  --sku Basic --vm-size C0
```

2. **Deploy Code**
```bash
# Build and push the container
az acr build --registry babellibraryacr --image library-of-babel:latest .

# Point the web app at the pushed container
az webapp config container set \
  --name babel-library-api \
  --resource-group babel-library-rg \
  --container-image-name babellibraryacr.azurecr.io/library-of-babel:latest \
  --container-registry-url https://babellibraryacr.azurecr.io
```

### Option 3: Azure Container Instances

```bash
# Build and push image
az acr build --registry babel-library-acr --image library-of-babel:latest .

# Deploy container
az container create --resource-group babel-library-rg \
  --name babel-library-container \
  --image babel-library-acr.azurecr.io/library-of-babel:latest \
  --ports 8000 \
  --dns-name-label babel-library \
  --restart-policy Always
```

## 📖 API Documentation

### Base URL
```
https://{your-app-service-name}.azurewebsites.net
```

### Endpoints

#### GET /api/books/{book_id}
Retrieve a specific book by its identifier.

**Parameters:**
- `book_id` (string, required): The unique book identifier (base-25 encoded)

**Response:**
```json
{
  "id": "abc123...",
  "content": "The text of the book...",
  "pages": 410,
  "lines_per_page": 40,
  "chars_per_line": 80,
  "generated_at": "2024-01-01T00:00:00Z"
}
```

#### GET /api/books/random
Get a random book from the library.

**Response:** Same as GET /api/books/{book_id}

#### GET /api/search
Search for books containing specific text.

**Query Parameters:**
- `q` (string, required): Text to search for
- `limit` (integer, optional): Maximum results (default: 10)

**Response:**
```json
{
  "query": "search text",
  "results": [
    {
      "book_id": "abc123...",
      "matches": [{"page": 1, "line": 5, "position": 10}],
      "score": 0.95
    }
  ],
  "total_results": 1000,
  "search_time_ms": 150
}
```

#### GET /api/stats
Get library statistics.

**Response:**
```json
{
  "total_possible_books": "10^1834100",
  "cached_books": 1500,
  "storage_used_gb": 2.5,
  "requests_today": 4500,
  "average_generation_time_ms": 15
}
```

## 🧠 Research Papers & Model Providers

### 🔬 Foundational Research

This project builds upon theoretical work in combinatorics, information theory, and computational linguistics. The following research papers provide the mathematical and conceptual foundation for exploring the Library of Babel.

#### Core Mathematical Foundations

1. **"The Library of Babel" - Jorge Luis Borges (1941)**
   - Original short story that inspired this project
   - [Read Online](https://www.cervantesvirtual.com/obra-visor/the-library-of-babel--0/html/)
   - **Key Concept**: Infinite library containing all possible books

2. **"The Total Library" - Jorge Luis Borges (1939)**
   - Essay exploring the concept of exhaustive libraries
   - Discusses the implications of infinite permutations

3. **"Borges and the Mathematical Infinite" - Guillermo Martinez (2013)**
   - Mathematical analysis of Borges' work
   - Explores the combinatorial aspects of the Library

#### Combinatorics & Information Theory

4. **"A Mathematical Theory of Communication" - Claude E. Shannon (1948)**
   - Foundational paper in information theory
   - [PDF](https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf)
   - **Relevance**: Calculating information content and entropy of books

5. **"The Number of Possible Chess Games" - Various Authors**
   - Similar combinatorial explosion to the Library of Babel
   - **Shannon Number**: 10^120 possible chess games

6. **"On the Capacity of the Human Channel" - George A. Miller (1956)**
   - The Magical Number Seven, Plus or Minus Two
   - [PDF](https://psychclassics.yorku.ca/Miller/)
   - **Relevance**: Human cognition limits in perceiving library content

### 🤖 AI & Language Model Research

#### Mistral AI

Mistral AI's work on efficient large language models provides insights into how we might analyze and understand the content within the Library of Babel.

1. **"Mistral 7B" - Mistral AI (2023)**
   - Efficient 7-billion parameter language model
   - [Paper](https://arxiv.org/abs/2310.06825)
   - [GitHub](https://github.com/mistralai/mistral-src)
   - **Relevance**: Understanding language patterns that might emerge in the Library

2. **"Mixtral of Experts" - Mistral AI (2024)**
   - Sparse Mixture of Experts model
   - [Paper](https://arxiv.org/abs/2401.04088)
   - **Relevance**: Efficient processing of diverse text patterns

3. **"LLaMA: Open and Efficient Foundation Language Models" - Meta (2023)**
   - Open-source language models
   - [Paper](https://arxiv.org/abs/2302.13971)
   - **Relevance**: Baseline for text analysis and generation

#### Anthropic

Anthropic's research on constitutional AI and interpretability helps us understand how to make sense of the Library's content.

4. **"Constitutional AI: Harmlessness from AI Feedback" - Anthropic (2022)**
   - [Paper](https://arxiv.org/abs/2212.08073)
   - **Relevance**: Filtering and understanding meaningful vs. random content

5. **"Scaling Relationships for Reward Model Overoptimization" - Anthropic (2023)**
   - [Paper](https://arxiv.org/abs/2310.12833)
   - **Relevance**: Understanding the boundaries between meaningful and random text

6. **"Interpretability in the Wild: A Circuit for Indirect Object Identity" - Anthropic (2023)**
   - [Paper](https://arxiv.org/abs/2309.17077)
   - **Relevance**: Analyzing patterns and structures within generated text

#### OpenAI

OpenAI's foundational work on language models and text generation provides the technical basis for exploring the Library.

7. **"Language Models are Few-Shot Learners" - OpenAI (2020)**
   - GPT-3 paper
   - [Paper](https://arxiv.org/abs/2005.14165)
   - **Relevance**: Understanding text generation at scale

8. **"Improving Language Understanding by Generative Pre-Training" - OpenAI (2018)**
   - Original GPT paper
   - [Paper](https://s3-us-west-2.amazonaws.com/openai-assets/research-papers/language_unsupervised/language_understanding_paper.pdf)
   - **Relevance**: Foundational work on transformers and text generation

9. **"Scaling Laws for Neural Language Models" - OpenAI (2020)**
   - [Paper](https://arxiv.org/abs/2001.08361)
   - **Relevance**: Understanding the relationship between model size and capability

10. **"DALL·E: Creating Images from Text" - OpenAI (2021)**
    - [Paper](https://arxiv.org/abs/2102.12092)
    - **Relevance**: Multi-modal understanding of generated content

11. **"GPT-4 Technical Report" - OpenAI (2023)**
    - [Paper](https://arxiv.org/abs/2303.08774)
    - **Relevance**: State-of-the-art in language model capabilities

### 📊 Research Applications

The Library of Babel serves as a unique testbed for various AI and linguistic research:

1. **Language Emergence**: Study how meaningful language might emerge from random permutations
2. **Information Theory**: Empirical testing of Shannon's theories
3. **Computational Linguistics**: Analysis of text patterns and structures
4. **Cryptography**: Understanding randomness and patterns in text
5. **Philosophy of Language**: Exploring the nature of meaning and communication

## 🛠️ Project Structure

```
library-of-babel/
├── src/                          # Main source code
│   ├── __init__.py
│   ├── main.py                   # FastAPI application
│   ├── config.py                 # Configuration settings
│   ├── models/                   # Data models
│   │   ├── book.py               # Book model and generation
│   │   ├── encoding.py           # Character encoding schemes
│   │   └── library.py            # Library structure
│   ├── services/                 # Business logic
│   │   ├── generation.py         # Book generation service
│   │   ├── search.py             # Search functionality
│   │   └── cache.py              # Caching service
│   ├── api/                      # API routes
│   │   ├── books.py              # Book endpoints
│   │   ├── search.py             # Search endpoints
│   │   └── stats.py              # Statistics endpoints
│   └── utils/                    # Utility functions
│       ├── math_utils.py         # Mathematical utilities
│       └── text_utils.py         # Text processing
├── tests/                        # Test files
│   ├── test_generation.py
│   ├── test_encoding.py
│   └── test_api.py
├── docs/                         # Documentation
│   ├── api.md                    # API documentation
│   ├── architecture.md           # Architecture overview
│   └── research.md               # Research notes
├── scripts/                      # Utility scripts
│   └── test_basic.py             # Basic project smoke test
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
├── .dockerignore
├── .gitignore
└── README.md                     # This file

GitHub workflows live at the repository root in `.github/workflows/`.
```

## 📦 Dependencies

### Core Dependencies
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
gunicorn>=21.0.0
pydantic>=2.5.0
azure-functions>=1.14.0
azure-storage-blob>=12.18.0
redis>=5.0.0
```

### Development Dependencies
```
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.25.0
black>=23.10.0
flake8>=6.1.0
mypy>=1.6.0
```

## 🔍 Environment Variables

Create a `.env` file in the project root:

```bash
# Application
APP_NAME=Library of Babel
APP_VERSION=1.0.0
DEBUG=true
PORT=8000

# Azure Configuration
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_REDIS_CONNECTION_STRING=your_redis_connection
AZURE_BLOB_CONTAINER=books

# Cache Settings
CACHE_ENABLED=true
CACHE_TTL=3600

# Generation Settings
BOOK_PAGES=410
BOOK_LINES_PER_PAGE=40
BOOK_CHARS_PER_LINE=80
ALPHABET=abcdefghijklmnopqrstuvwxyz ,.
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_generation.py

# Run with verbose output
pytest -v
```

## 📊 Monitoring & Analytics

### Azure Application Insights
```bash
# Enable Application Insights
az monitor app-insights create --resource-group babel-library-rg \
  --name babel-library-insights \
  --location eastus

# View logs
az monitor app-insights query --app babel-library-insights \
  --query "requests | summarize count() by bin(timestamp, 1h)"
```

### Custom Metrics
- Book generation time
- Cache hit rate
- Search query performance
- Storage usage
- API response times

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Guidelines
- Follow PEP 8 style guide
- Include type hints
- Add docstrings to all functions
- Write tests for new functionality
- Update documentation as needed

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Jorge Luis Borges for the original concept
- All contributors to open-source libraries used in this project
- The AI research community for their work on language models

## 📞 Contact

- **Project Lead**: [@mavilleg](https://github.com/mavilleg)
- **Issues**: [GitHub Issues](https://github.com/mavilleg/vibework/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mavilleg/vibework/discussions)

---

*"When it was proclaimed that the Library contained all books, the first impression was one of extravagant happiness."* - Jorge Luis Borges

*"I have always imagined that Paradise will be a kind of library."* - Jorge Luis Borges
