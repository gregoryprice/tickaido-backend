## Agent Knowledge Integration Options for Shipwell Backend

This document outlines practical designs to enable agents (Pydantic AI) to answer domain questions using Shipwell documentation and API references, e.g., “What endpoints can I use to create a location in Shipwell?”. It is tailored to this codebase: FastAPI backend, Pydantic AI agents created via `app/services/dynamic_agent_factory.py` with optional MCP toolsets, Postgres as primary DB, and no existing vector or graph components.

### Summary of Options
- Vector RAG with pgvector (recommended to start)
- Hybrid retrieval (BM25 + vector + rerank)
- Knowledge Graph (Neo4j) from OpenAPI + docs
- Combined: KG for precise candidates + Vector RAG for examples

---

## Option 1 — Vector RAG with pgvector (fastest path)

Best for high-quality Q&A grounded in docs/specs with low latency and minimal ops.

### Components
- Ingestion pipeline: crawl docs and parse `openapi.yaml`; chunk content; embed; store in Postgres with pgvector
- Retriever: vector similarity (optionally hybrid) with metadata filters and citations
- Agent tools: `kb_search`, `kb_get_doc` exposed directly in-agent or via MCP tool

### Postgres schema (pgvector)
```sql
-- One-time: enable pgvector (run in an Alembic migration)
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE IF NOT EXISTS kb_documents (
  id BIGSERIAL PRIMARY KEY,
  url TEXT UNIQUE NOT NULL,
  title TEXT,
  source TEXT,             -- e.g., shipwell_docs, openapi
  breadcrumbs TEXT[],
  updated_at TIMESTAMPTZ,
  raw_text TEXT
);

-- Chunks with embeddings
CREATE TABLE IF NOT EXISTS kb_chunks (
  id BIGSERIAL PRIMARY KEY,
  doc_id BIGINT REFERENCES kb_documents(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  text TEXT NOT NULL,
  token_count INT,
  section_path TEXT[],     -- e.g., {"API","Locations","Create"}
  embedding vector(1536)   -- match your embedding size
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_kb_chunks_doc_id ON kb_chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_fts ON kb_chunks USING GIN (to_tsvector('english', text));
-- Vector index choice depends on Postgres/pgvector version (HNSW recommended on PG16+)
-- Example IVFFlat (requires ANALYZE and good lists setting):
CREATE INDEX IF NOT EXISTS idx_kb_chunks_embedding ON kb_chunks USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
```

### Ingestion sketch (OpenAPI + docs)
```python
import yaml, re, asyncio
from datetime import datetime
from typing import Iterable
from httpx import AsyncClient
from pydantic import BaseModel

# 1) Parse OpenAPI operations to structured docs
class OperationDoc(BaseModel):
    url: str
    title: str
    text: str
    breadcrumbs: list[str]
    updated_at: datetime | None = None

def load_openapi_operations(path: str) -> list[OperationDoc]:
    spec = yaml.safe_load(open(path))
    ops = []
    for route, methods in spec.get("paths", {}).items():
        for method, meta in methods.items():
            title = meta.get("summary") or f"{method.upper()} {route}"
            desc = meta.get("description") or ""
            url = f"openapi://{method.upper()} {route}"
            text = f"Endpoint: {method.upper()} {route}\n{desc}\n\nParams: {meta.get('parameters', [])}\nRequestBody: {meta.get('requestBody', {})}"
            ops.append(OperationDoc(url=url, title=title, text=text, breadcrumbs=["OpenAPI" , route]))
    return ops

# 2) Crawl docs site (sitemap-based) and extract clean text (pseudo-code)
async def fetch_and_extract(urls: Iterable[str]) -> list[OperationDoc]:
    results = []
    async with AsyncClient(follow_redirects=True, timeout=15.0) as client:
        for url in urls:
            r = await client.get(url)
            html = r.text
            text = re.sub(r"\s+", " ", strip_html_but_keep_headings(html))  # implement extractor
            title = extract_title(html)
            breadcrumbs = extract_breadcrumbs(html)
            results.append(OperationDoc(url=url, title=title, text=text, breadcrumbs=breadcrumbs))
    return results

# 3) Chunk + embed + upsert (use your embedding model; size matches schema)
def chunk(text: str, max_tokens: int = 800, overlap: int = 100) -> list[str]:
    # implement token-aware chunking; placeholder below
    parts = []
    words = text.split()
    step = max_tokens - overlap
    for i in range(0, len(words), step):
        parts.append(" ".join(words[i:i+max_tokens]))
    return parts

async def embed_texts(texts: list[str]) -> list[list[float]]:
    # call OpenAI embeddings or your preferred provider
    # return list of vectors
    ...

async def upsert_docs_chunks(docs: list[OperationDoc]):
    for doc in docs:
        doc_id = await ensure_document(doc)  # insert or fetch existing by URL
        chunks = chunk(doc.text)
        vectors = await embed_texts(chunks)
        await insert_chunks(doc_id, chunks, vectors, section_path=doc.breadcrumbs)
```

### Retrieval (SQL + Python)
```sql
-- Vector similarity search (top K)
SELECT c.id, d.url, d.title, c.text, (c.embedding <=> :query_vec) AS score
FROM kb_chunks c
JOIN kb_documents d ON d.id = c.doc_id
ORDER BY c.embedding <=> :query_vec
LIMIT 5;
```

```python
from pydantic import BaseModel

class RetrievedChunk(BaseModel):
    url: str
    title: str
    snippet: str
    score: float
    section_path: list[str] | None = None

async def kb_search(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    q_vec = await embed_texts([query])
    rows = await db.fetch_all(
        """
        SELECT d.url, d.title, c.text AS snippet, (c.embedding <=> :q)::float AS score, c.section_path
        FROM kb_chunks c JOIN kb_documents d ON d.id = c.doc_id
        ORDER BY c.embedding <=> :q LIMIT :k
        """,
        {"q": q_vec[0], "k": top_k},
    )
    return [RetrievedChunk(**r) for r in rows]
```

### Pydantic AI agent tool (direct or via MCP)
```python
from pydantic_ai.tools import Tool

kb_search_tool = Tool(
    name="kb_search",
    description="Search Shipwell docs/OpenAPI KB and return cited snippets",
    args_schema={"query": str, "top_k": int},
    handler=lambda query, top_k=5: kb_search(query, top_k)
)

# When constructing the agent in DynamicAgentFactory, include kb_search_tool
# or expose via your MCP server as a tool if you prefer isolation.
```

### Example answer flow (user question)
Query: “what endpoints can I use to create a location in Shipwell?”
1) Agent embeds query → `kb_search("create location endpoint Shipwell")`
2) Results include OpenAPI-derived `POST /locations` + docs pages
3) Agent composes:
   - Endpoints list (method + path)
   - Example request/response (from best-matching snippet)
   - Citations with `url` and section title

### Tradeoffs
- Pros: simplest infra, leverages existing Postgres; strong answers with citations
- Cons: relations are implicit; advanced multi-hop reasoning benefits from a KG

---

## Option 2 — Hybrid retrieval (BM25 + Vector + rerank)

Improves exact-field and keyword matching while keeping semantic coverage.

### Index additions
- Keep `kb_chunks` and add a GIN FTS index (shown above)

### Retrieval strategy
```sql
-- BM25 candidate set (fts)
SELECT c.id, d.url, d.title, c.text, ts_rank_cd(to_tsvector('english', c.text), plainto_tsquery(:q)) AS bm25
FROM kb_chunks c JOIN kb_documents d ON d.id = c.doc_id
WHERE to_tsvector('english', c.text) @@ plainto_tsquery(:q)
ORDER BY bm25 DESC LIMIT 50;
```

Combine with top-50 vector results, then rerank with a cross-encoder or simple linear mix. Latency increases modestly; relevance improves on API field names and error codes.

### Tradeoffs
- Pros: better on exact tokens/field names; robust for API lookups
- Cons: slightly higher complexity and latency; add reranker for best results

---

## Option 3 — Knowledge Graph (Neo4j) from OpenAPI + docs

Adds structured relationships for precise endpoint/resource queries and multi-hop reasoning.

### Graph model (example)
- Nodes: `Resource{name}`, `Endpoint{method,path,version}`, `Operation{type}` (create/read/update/delete), `Field{name}`, `DocPage{url,title}`
- Edges: `RESOURCE_HAS_ENDPOINT`, `OPERATION_TYPE`, `USES_FIELD`, `DOC_DESCRIBES`, `RELATED_TO`

### Ingestion (OpenAPI → KG)
```python
from neo4j import GraphDatabase

def upsert_endpoint(tx, resource: str, method: str, path: str, doc_url: str | None):
    tx.run(
        """
        MERGE (r:Resource {name: $resource})
        MERGE (e:Endpoint {method: $method, path: $path})
        MERGE (r)-[:RESOURCE_HAS_ENDPOINT]->(e)
        WITH e
        FOREACH (u IN CASE WHEN $doc_url IS NULL THEN [] ELSE [$doc_url] END |
          MERGE (d:DocPage {url: u}) MERGE (e)-[:DOC_DESCRIBES]->(d)
        )
        """,
        resource=resource, method=method.upper(), path=path, doc_url=doc_url,
    )
```

### Query (agent → Cypher)
User: “create a location”
```cypher
MATCH (r:Resource {name: 'location'})-[:RESOURCE_HAS_ENDPOINT]->(e:Endpoint)
MATCH (e)-[:OPERATION_TYPE]->(o:Operation {type: 'create'})
OPTIONAL MATCH (e)-[:DOC_DESCRIBES]->(d:DocPage)
RETURN e.method AS method, e.path AS path, d.url AS url
```

Agent then augments with examples via vector search over docs (Option 4 below).

### Tradeoffs
- Pros: exact, structured answers; great for “which endpoints?” or dependency trails
- Cons: new infra; schema and ingestion maintenance; higher complexity

---

## Option 4 — Combined KG + Vector (recommended for APIs)

Use KG to identify precise endpoint candidates; use vector RAG to fetch best examples/snippets and prose context; answer with citations.

### Flow
1) KG query returns candidates for resource + operation (e.g., `POST /locations`)
2) Vector search retrieves example requests/responses, field explanations
3) Agent composes a grounded answer with links to docs/spec section

### Minimal agent tool surface
```python
from pydantic import BaseModel

class Endpoint(BaseModel):
    method: str
    path: str
    title: str | None = None
    doc_url: str | None = None

async def graph_find_endpoints(resource: str, operation: str) -> list[Endpoint]: ...
async def kb_search(query: str, top_k: int = 5) -> list[dict]: ...  # {url,title,snippet,score}

# Agent policy: Prefer KG; fall back to vector if KG empty or low confidence
```

---

## Integration with this codebase

- Agents are created via `DynamicAgentFactory` using Pydantic AI, optionally with MCP toolsets (`mcp_client`).
- Expose `kb_search` (and optionally `graph_find_endpoints`) either:
  - Directly as Pydantic AI tools when instantiating agents, or
  - As MCP tools in `mcp_server/tools/` (preferred for isolation, auditing, and auth) and allowlist them per agent.
- Use existing Postgres for pgvector (Option 1/2). For KG, run Neo4j externally and add a small client wrapper in an MCP tool.

### MCP tool example (kb_search)
```python
# mcp_server/tools/kb_tools.py
from fastmcp import mcp
from .db import kb_search  # your implementation above

def register_kb_search():
    @mcp.tool()
    async def kb_search_tool(query: str, top_k: int = 5) -> str:
        results = await kb_search(query, top_k)
        # Return JSON string for transport
        return json.dumps([r.model_dump() for r in results])
```

Then allowlist `kb_search_tool` for agents via `tools_enabled` in your agent config and `DynamicAgentFactory` will pass through the filtered MCP toolset.

---

## Security, governance, and ops
- Domain allowlist for any live web fetch tools; respect `robots.txt` and rate limits
- Sanitize HTML; strip scripts; avoid executing embedded content
- PII redaction in logs; only store necessary metadata in KB
- Observability: log query → candidate set (scores) → selected context → citations
- Freshness: daily incremental recrawl; admin endpoint to refresh a URL immediately

---

## Tradeoffs overview
- **Vector RAG**: low complexity, fast, great baseline. Relations are implicit.
- **Hybrid**: better exact matches; modest complexity/latency increase.
- **Knowledge Graph**: precise, structured, multi-hop; highest complexity.
- **Combined KG+Vector**: best overall quality for APIs; two systems to operate.

---

## Acceptance criteria for “location endpoints” query
- Returns `POST /locations` (and any versioned variants) with at least one example request and 2+ citations
- ≥90% precision on 20 curated API queries
- P50 latency ≤ 2.5s (Vector/Hybrid), ≤ 3.5s (KG+Vector)
- Telemetry dashboard shows retrieval score distributions and tool usage

---

## Next steps
1) Implement Option 1 (pgvector) ingestion + retrieval
2) Add `kb_search` MCP tool and allowlist for relevant agents
3) Evaluate Hybrid; if precision needs improve, add BM25 + rerank
4) If questions increasingly require structured joins, implement KG subset (Endpoints/Resources/Operations) and combine


---

## Indexing lifecycle: add/update/remove documents

This section describes how content is made searchable under each option, and how to add or remove documents.

### Common concepts
- Document identity: Use stable `url` (docs page URL or `openapi://METHOD PATH`) as unique key.
- Deduplication: Compute a content hash to skip unchanged pages.
- Chunking: Token-aware chunks with overlap for better recall and snippet quality.
- Embeddings: Single provider and dimension across all chunks (e.g., 1536).
- Metadata: Store `title`, `breadcrumbs`, `source`, `updated_at` for filtering and citation.

### Vector RAG (Option 1)
#### Add documents
1) Discover new URLs (sitemap, API list, manual additions)
2) Fetch and extract clean text
3) Upsert `kb_documents` by `url`
4) Chunk → embed → insert into `kb_chunks` (delete old chunks for this doc first)

#### Update documents
1) Re-fetch URL; compute content hash
2) If hash changed: update `kb_documents.updated_at`, delete existing chunks for `doc_id`
3) Re-chunk, re-embed, re-insert

#### Remove documents
1) Delete from `kb_documents` by URL; `ON DELETE CASCADE` removes `kb_chunks`

#### Searchability
- Vector search on `kb_chunks.embedding`, optionally combined with FTS for hybrid relevance.
- Citations come from joined `kb_documents.url` and `title`.

### Hybrid retrieval (Option 2)
Same add/update/remove as Vector RAG. Additional step:
- Maintain FTS index (`idx_kb_chunks_fts`) and optionally a materialized view for BM25 if needed.

#### Searchability
- Run FTS and vector searches in parallel; union top candidates; rerank to top-K.

### Knowledge Graph (Option 3)
#### Add documents (from OpenAPI and docs)
- OpenAPI: Derive nodes/edges for `Resource`, `Endpoint`, `Operation`, `Field`, `DocPage`.
- Docs: Create/merge `DocPage` nodes; relate to endpoints (`DOC_DESCRIBES`) via heuristics (link text, headings, or manual mapping file).

#### Update documents
- Re-run OpenAPI ingestion on spec changes (idempotent MERGE operations)
- Re-crawl docs; update `DocPage` properties (e.g., title) and maintain relations

#### Remove documents
- Detach-delete `DocPage` nodes for removed URLs; prune orphaned nodes if desired

#### Searchability
- Agent translates intent to Cypher (e.g., endpoints for resource=location, operation=create)
- Return candidates; augment with vector snippets from doc text (Option 4)

### Combined KG + Vector (Option 4)
- Follow KG add/update/remove for structured entities
- Maintain vector index for full-text examples and explanations
- Search path: KG → candidates → vector snippets → compose answer with citations

### Ops considerations
- Scheduling: Nightly incremental crawl + weekly full crawl; on-demand refresh endpoint (`POST /admin/kb/refresh?url=...`)
- Monitoring: Track ingestion successes/failures, changed pages count, average embedding latency, index sizes
- Rollback: Keep previous embedding version for quick rollback if a bad model release degrades quality
- Access control: Store `source` and optional `org_id` to filter per-tenant content if needed later



---

## LangChain RAG: URLs, documents, files, and knowledge sources

This section shows a generic, library-backed approach using LangChain to ingest URLs, files, and other knowledge into a vector database, then retrieve context for agents. You can plug different vector stores (Chroma, Qdrant, Pinecone, pgvector) and embedding models.

### Components
- Loaders: `WebBaseLoader`, `SitemapLoader`, `DirectoryLoader`, `Unstructured*` loaders for PDFs, DOCX, etc.
- Splitters: `RecursiveCharacterTextSplitter` with overlap for context preservation
- Embeddings: `OpenAIEmbeddings` (or Azure/Open source alternatives)
- Vector store: Chroma (local dev), pgvector (existing Postgres), or hosted (Qdrant/Pinecone)
- Retriever: `as_retriever()` with k, score threshold, filters
- RAG chain: `create_retrieval_chain` or custom prompt + combine docs

### Ingesting web URLs
```python
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# 1) Load
loader = WebBaseLoader([
  "https://docs.shipwell.com/some-page",
  "https://intercom.help/shipwell/en/articles/..."])
docs = loader.load()

# 2) Split
splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)
splits = splitter.split_documents(docs)

# 3) Embed + persist to vector store (Chroma example)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma(collection_name="shipwell_kb", embedding_function=embeddings, persist_directory=".chroma")
vectorstore.add_documents(splits)
vectorstore.persist()
```

### Ingesting files (PDF, DOCX, Markdown)
```python
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, UnstructuredWordDocumentLoader, UnstructuredMarkdownLoader

file_loader = DirectoryLoader(
  path="/data/docs",
  glob="**/*",
  loader_cls=lambda p: PyPDFLoader(p) if p.suffix.lower()==".pdf" else (
      UnstructuredWordDocumentLoader(p) if p.suffix.lower() in {".docx",".doc"} else UnstructuredMarkdownLoader(p)
  )
)
file_docs = file_loader.load()
splits = splitter.split_documents(file_docs)
vectorstore.add_documents(splits)
vectorstore.persist()
```

### Using pgvector instead of Chroma
```python
from langchain_postgres.vectorstores import PGVector

connection = "postgresql+psycopg2://user:pass@localhost:5432/ai_tickets"
collection = "shipwell_kb"
pg_vs = PGVector.from_documents(
  documents=splits,
  embedding=embeddings,
  connection=connection,
  collection_name=collection,
  use_jsonb=True  # store metadata
)
```

### Building a retriever and RAG chain
```python
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

prompt = ChatPromptTemplate.from_template(
  """
  You are a Shipwell assistant. Answer using the context. Cite sources with titles and URLs.
  Question: {question}
  Context:
  {context}
  """
)

def format_docs(docs):
    return "\n\n".join(f"[{d.metadata.get('source')}]\n{d.page_content[:1200]}" for d in docs)

chain = (
  {"context": retriever | format_docs, "question": RunnablePassthrough()}
  | prompt
  | ChatOpenAI(model="gpt-4o-mini")
)

answer = chain.invoke("what endpoints can I use to create a location in Shipwell?")
```

### Wiring into your agent (two paths)
1) As a direct tool: Wrap `retriever.get_relevant_documents` in a function exposed to Pydantic AI agents.
2) As an MCP tool: Host a small FastAPI/FastMCP endpoint that executes the retrieval and returns JSON with `title`, `url`, `snippet`, `score`.

### Adding/removing documents with LangChain
- Add: Run the same loader/splitter to produce `Document`s with `metadata={"source": url_or_path, ...}` and add to the vector store.
- Update: Re-load and upsert with a stable `id`/`source` metadata. For Chroma, use `ids` to delete + re-add; for PGVector, use upsert by `source`.
- Remove: Delete by `id` or `source` filter in the vector store.

### Vector DB choices and tradeoffs
- Chroma: simple, local persistence, good for dev; not ideal for prod scale.
- PGVector: fits your stack, transactional, easy ops; good baseline performance.
- Qdrant/Pinecone: managed scaling, advanced indexing/reranking; extra infra/cost.

### Notes for production
- Standardize embeddings model and dimension; version embeddings for rollbacks.
- Normalize/clean HTML; keep headings and code blocks; avoid scripts.
- Add BM25 hybrid on top of LangChain retrievers if exact field matching matters.
- Cache HTTP fetches; deduplicate by content hash.
