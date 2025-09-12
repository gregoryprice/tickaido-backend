name: "Agent Knowledge Integration PRP"
description: |

  ## Purpose
  Enable Pydantic AI agents to answer domain questions using Shipwell documentation and API specs with grounded citations.

  ## Goal
  - Implement a production-ready knowledge pipeline and retrieval layer powering questions like:
    - "What endpoints can I use to create a location in Shipwell?"
    - "Which fields are required for posting a shipment?"

  ## Why
  - Reduce support and onboarding friction by surfacing authoritative answers inline.
  - Improve agent reliability with citations to Shipwell docs and OpenAPI spec.

  ## What (MVP: Vector RAG with pgvector)
  - Ingestion: Parse `openapi.yaml`; crawl docs; chunk→embed→store in Postgres (pgvector)
  - Retrieval: Vector similarity (hybrid optional), return 3–5 cited snippets
  - Agent tools: `kb_search` via MCP, allowlisted per agent in `DynamicAgentFactory`
  - Admin endpoints: refresh a URL; reindex OpenAPI; stats

  ### Success Criteria
  - [ ] Answers include ≥2 citations per response
  - [ ] ≥90% precision on 20 curated API/domain queries
  - [ ] P50 latency ≤2.5s (vector); ≤3.5s (hybrid)
  - [ ] Telemetry shows retrieval scores and tool usage

  ## Needed Context
  ```yaml
  - file: openapi.yaml
    why: Authoritative source for endpoints and fields

  - file: app/services/dynamic_agent_factory.py
    why: Hook MCP tools into Pydantic AI agents

  - file: mcp_server/tools/
    why: Place kb tools; follow ticket tool patterns

  - doc: https://github.com/pgvector/pgvector
    section: Indexing (IVFFlat/HNSW)
    critical: Match embedding dimension; analyze table for IVFFlat

  - doc: https://platform.openai.com/docs/guides/embeddings
    section: Text Embeddings
    critical: Consistent model; cost/latency tradeoffs
  ```

  ## Implementation Blueprint

  ### Data models
  - DB tables: `kb_documents`, `kb_chunks` with `vector` column (see `docs/agent-knowledge-integration.md`)

  ### Tasks (ordered)
  ```yaml
  Task 1: Add Alembic migration to create kb tables and pgvector extension
  Task 2: Implement ingestion script for OpenAPI → docs (chunk, embed, upsert)
  Task 3: Implement docs crawler/extractor with sitemap + allowlist
  Task 4: Implement `kb_search` function and MCP tool wrapper
  Task 5: Wire tool into agents via `DynamicAgentFactory` (allowlist)
  Task 6: Add admin endpoints: refresh URL, reindex spec, stats
  Task 7: Observability: log retrieval scores, citations; basic dashboard
  ```

  ### Pseudocode (critical snippets)
  ```python
  async def upsert_document(url: str, title: str, text: str, source: str, breadcrumbs: list[str]):
      doc_id = await db.fetch_val("INSERT INTO kb_documents(url,title,source,breadcrumbs,updated_at,raw_text) VALUES(:u,:t,:s,:b,now(),:r) ON CONFLICT (url) DO UPDATE SET title=:t, source=:s, breadcrumbs=:b, updated_at=now(), raw_text=:r RETURNING id", {"u":url, "t":title, "s":source, "b":breadcrumbs, "r":text})
      await db.execute("DELETE FROM kb_chunks WHERE doc_id=:d", {"d": doc_id})
      parts = chunk(text)
      vecs = await embed_texts(parts)
      await db.executemany("INSERT INTO kb_chunks(doc_id,chunk_index,text,token_count,section_path,embedding) VALUES(:d,:i,:x,:n,:p,:e)", [
          {"d": doc_id, "i": i, "x": part, "n": estimate_tokens(part), "p": breadcrumbs, "e": vec}
          for i, (part, vec) in enumerate(zip(parts, vecs))
      ])
  ```

  ### Integration Points
  ```yaml
  DATABASE:
    - migration: create kb tables; enable pgvector

  CONFIG:
    - add: embeddings model name; crawl allowlist; max_concurrency

  ROUTES:
    - add: /admin/kb/refresh, /admin/kb/reindex_openapi, /admin/kb/stats

  MCP TOOLS:
    - add: kb_tools.py with kb_search_tool
  ```

  ## Ops & Lifecycle
  - Nightly incremental crawl; weekly full rebuild
  - On-demand refresh endpoint
  - Versioned embeddings to allow rollback
  - Cost controls: batch embeddings; cache HTTP; cap tokens

  ## Future Phases
  - Hybrid retrieval (BM25 + vector + rerank)
  - Knowledge Graph (Neo4j) for endpoints/resources/operations; combine with vector


