This system is designed to crawl documentation websites, process the content, and enable efficient searching using both semantic and keyword-based techniques. 

## Pipeline Stages

### 1. Crawling & Scraping

The process begins with web crawling and scraping. The system uses `crawl4ai` to fetch documentation efficiently. It supports sitemap-based crawling when available and limits the crawl depth using `settings.MAX_DEPTH`. To improve relevance and remove unwanted URLs, there is URL filtering with GPT. The crawler also extracts hidden code snippets from interactive elements while preserving the original structure of the documentation.

### 2. Chunking

Once the data is collected, it is divided into chunks for improved search efficiency. Two types of chunking are applied:

- **Normal Chunks:** Breaks the content into meaningful sections, ensuring that code snippets remain linked to relevant context.
- **Summary Chunks:** Creates high-level overviews of documentation sections, capturing key details about SDKs and frameworks to enhance search context.

### 3. Embeddings Generation

To enable effective search functionality, a hybrid embedding approach is used:

- **Dense Embeddings:** Generated using the `bge-base-1.5` model, these embeddings capture the semantic meaning of the content, allowing for similarity-based searches.
- **Sparse Embeddings:** Created using BM25 encoding, these embeddings preserve keyword importance, improving exact phrase matching.

### 4. Storage & Indexing

The processed data is stored in Pinecone, along with metadata such as:

- SDK or framework name
- Source URL
- Base URL
- Category (e.g., AI, Cloud, Web, Mobile)
- Presence of code snippets
- Version information (if available)
- Indicator for summary chunks

### 5. Search & Retrieval

The search system operates through `query_route` and combines both semantic and keyword search techniques. A configurable alpha parameter allows balancing between the two methods. Users can refine searches by applying metadata filters, such as restricting results to AI-related content. Re-ranking is also implemented to improve the quality of search results.

## Frontend Interface

A frontend interface built with Streamlit is available in `app.py`. It provides:

- A document-crawling page
- Options for customizing search parameters
- Results visualization
- Metadata filtering for refined searches

## Installation

```markdown

1. Clone the repository:

git clone <repository-url>

```

Create and activate a virtual environment:

```bash
python -v env env
source env/bin/activate 
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the src directory with the following variables:

```
PINECONE_API_KEY=your_pinecone_key
OPENAI_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
INDEX_NAME=your_index_name
INDEX_HOST=your_index_host
JINA_API_KEY=your_jina_key
MONGO_URI=your_mongo_uri
MONGODB_DB_NAME=your_db_name
ERROR_COLLECTION_NAME=error_logs
MAX_DEPTH=3
MAX_LLM_REQUEST_COUNT=50
MAX_CONCURRENT_CLICKS=15
LLM_USAGE_COLLECTION_NAME=llm_usage
USER_DATA=user_data
CHUNK_SEMAPHORE=40
OPENAI_BASE_URL=https://api.openai.com
OPENAI_COMPLETION_ENDPOINT=/v1/chat/completions
OPENAI_FILE_ENDPOINT=/v1/files
OPENAI_MODEL=open_ai_model
OPENAI_BATCH_ENDPOINT=/v1/batch
PINECONE_LIST_INDEX_URL
PINECONE_API_VERSION
PINECONE_CREATE_INDEX_URL
PINECONE_UPSERT_URL
PINECONE_QUERY_URL
JINA_RERANKING_MODEL
JINA_RERANKING_URL

```

## Running the Application

1. Start the FastAPI server:

```bash
uvicorn src.app.main:app --reload
```

1. Launch the Streamlit interface:

```bash
streamlit run src/frontend/app.py
```

## Project Structure

- src
    - `app/` - Main application code
        - `config/` - Configuration settings
        - `controllers/` - Request handlers
        - `models/` - Data models and schemas
        - `repositories/` - Database interactions
        - `routes/` - API endpoints
        - `services/` - Business logic
        - `usecases/` - Use case implementations
        - `utils/` - Utility functions
    - `frontend/` - Streamlit web interface

## API Endpoints

- `POST /` - Start crawling process for given URLs
- `POST /query` - Search indexed documents

## Dependencies

Key dependencies include:

- FastAPI
- Streamlit
- OpenAI API
- Pinecone
- MongoDB
- Playwright
- FastEmbed
- Crawl4AI
- aiohttp
- pydantic