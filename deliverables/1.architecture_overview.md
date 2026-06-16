# Architecture Overview

## 🔄 End-to-End Data Flow

```
User Query → Front Router (Intent Classification) 
  → Retriever Agent (Vector Search + FGA Filter) 
  → Specialist Agent (LLM Synthesis) 
  → Reviewer Agent (Hallucination Detection) 
  → Response Delivery
```

### Off-Topic Short-Circuit
Deterministic keywords block irrelevant queries immediately, skipping LLM/Weaviate entirely. No tokens spent, no database calls.

---

## 📥 Ingestion Pipeline

1. **Document Crawling**: PDF files stored in `backend/data/public` and `backend/data/private`
2. **Chunking**: `RecursiveCharacterTextSplitter` (chunk_size=1000, overlap=150)
3. **Embedding**: HuggingFace `all-MiniLM-L6-v2` model
4. **Metadata Enrichment**: Each chunk tagged with `doc_id` and `allowed_role` (collaborator or admin)
5. **Storage**: Indexed in Weaviate Cloud with document-level access control markers

---

## 🔍 Retrieval Strategy

- **Vector Search**: Semantic similarity via embeddings (k=5 nearest neighbors)
- **Query Rewriting**: Gemini rewrites user intent → optimized search terms
- **FGA Interception Layer**: Post-retrieval authorization filtering
- **Authorization Enforcement**: `SafeIdRetriever` ensures document IDs are stable for FGA batch checks
- **Result Filtering**: Only documents passing FGA authorization checks reach the LLM

---

## 🧠 LLM Orchestration Layer

### Prompt Construction
1. **System Prompt**: Defines strict compliance boundaries for Specialist
2. **Context Injection**: Authorized doc chunks formatted as `[Source: doc:X]: text`
3. **User Query**: Original intent preserved in payload

### Context Management
- Specialist Agent receives only authorized chunks
- Reviewer Agent has full access to same context for validation
- Self-healing loop: Rejection → Specialist retries (up to 3 attempts)

---

## 🔐 Authentication & Access Control

### Fine-Grained Authorization (FGA) Model
- **Auth System**: OpenFGA (Auth0 / Local)
- **Relation Tuples**: `user:role relation:"viewer" object:"doc:X"`
- **Enforcement Point**: After Weaviate retrieval, before LLM synthesis

### Role-Based Access
- **Collaborator**: Access to public docs (grievance, whistleblower, terms, service guide)
- **Admin**: Access to all docs including private (chatbot_takehome_assignment)
- **Batch Authorization**: FGA client performs atomic permission checks on retrieved documents

---

## 🏢 Multi-Tenancy & Department-Level Isolation

### Strategy
1. **Logical Partitioning**: Extend FGA schema with `department:X` entities
2. **Tuple Structure**: `user:alice@dept-sales relation:"viewer" object:"doc:sales_guide"`
3. **Weaviate Metadata**: Add `department` field to chunk metadata
4. **Retrieval Filter**: Pre-query parameter to filter by active user's department
5. **Authorization Rules**: FGA relations enforce department boundaries at policy level

### Implementation Path
- Extend `ClientTuple` tuples to include department scopes
- Update `mock_users.json` with department assignments
- Modify retrieval query to include department filter condition
- FGA authorization enforces both role AND department constraints

---

## 🏗️ System Components

| Component | Role | Technology |
|-----------|------|-----------|
| **Frontend** | User interface & SSO simulation | Streamlit |
| **Backend API** | Request orchestration | FastAPI |
| **Front Router** | Intent classification | Deterministic rules + Gemini |
| **Retriever Agent** | Semantic search + Auth | Weaviate + OpenFGA |
| **Specialist Agent** | Response synthesis | Gemini LLM |
| **Reviewer Agent** | Quality gate | Gemini LLM |
| **Vector Store** | Semantic search backend | Weaviate Cloud |
| **Auth System** | Fine-grained authorization | OpenFGA (Auth0/Local) |

