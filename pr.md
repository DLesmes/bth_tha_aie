┌──────────────────────┐
│ Streamlit UI Frontend│ (Port 8501)
└──────────┬───────────┘
│
POST /api/chat [Payload + Identity Attributes]
│
▼
┌──────────────────────┐
│   FastAPI Gateway    │ (Port 8000)
└──────────┬───────────┘
│
▼
┌──────────────────────┐
│  LangGraph Engine    │ (State Machine Layer)
└────┬────────────┬────┘
│            │
Query + Roles │            │ Chunks
▼            ▼
┌───────────┐        ┌──────────────┐
│ Auth0 FGA │        │   Weaviate   │
│ Security  │        │ Cloud Hosted │
└───────────┘        └──────────────┘

### Component Details
* **Package Manager:** `uv` (Fast Python package resolver and runner).
* **Frontend UI:** Streamlit container simulating user login (`admin` vs. `collaborator`).
* **Backend Gateway:** FastAPI application handling payload verification and LangGraph execution.
* **Orchestration Engine:** LangGraph coordinating asynchronous steps, state monitoring, and evaluation feedback.
* **Security Filter Layer:** Auth0 FGA (OpenFGA engine) intercepting data retrieval using relationship tuples.
* **Vector Engine:** Hosted Weaviate Cloud Sandbox Instance using local Hugging Face calculations (`all-MiniLM-L6-v2`).
* **Core Inference LLM:** Google Gemini (`gemini-3.5-flash`) via `langchain-google-genai`.

---

## 2. Directory Layout Architecture

```text
agentic-rag-demo/
├── .env                          # Master Environment configuration (git ignored)
├── architecture/
│   └── intial_architecture.png   # Referenced architecture diagram
├── frontend/
│   ├── Dockerfile
│   ├── app.py                    # Streamlit conversational interface
│   └── mock_users.json           # Local simulation RBAC identity database
└── backend/
    ├── Dockerfile
    ├── requirements.txt          # Explicit pinning specification for UV
    ├── index_setup.py            # Data parsing, vectorization & FGA configuration script
    ├── test_graph.py             # Sandbox offline state machine verification test
    ├── main.py                   # FastAPI service layer gateway
    └── src/
        ├── __init__.py
        ├── settings.py           # Master environment variables initialization class
        ├── state.py              # LangGraph structural memory type schemas
        ├── agents.py             # Agent runtime processors (Retriever, Specialist, Reviewer)
        └── agent_graph.py        # LangGraph topology and state logic router

3. Environment & Dependency Specifications
3.1 Master Environment Configuration (.env)
Place this at the root directory:
# Google Generative AI Configuration
GOOGLE_API_KEY="AIzaSyYourGoogleApiKeyHere"
MODEL_NAME="gemini-3.5-flash"

# Hosted Weaviate Cloud Infrastructure Settings
WEAVIATE_URL="[https://your-sandbox-cluster.weaviate.network](https://your-sandbox-cluster.weaviate.network)"
WEAVIATE_API_KEY="your-weaviate-cloud-api-key"

# Auth0 Fine-Grained Authorization Configuration
FGA_STORE_ID="your_fga_store_id"
FGA_CLIENT_ID="your_fga_client_id"
FGA_CLIENT_SECRET="your_fga_client_secret"
FGA_API_URL="[https://api.us1.fga.dev](https://api.us1.fga.dev)"

# Runtime Engine Defaults
DEFAULT_DEMO_ROLE="collaborator"
BACKEND_API_URL="http://localhost:8000/api/chat"

3.2 Backend Dependencies (backend/requirements.txt)
langchain-weaviate>=0.0.2
weaviate-client>=4.5.4
auth0-ai-langchain
openfga-sdk>=0.6.0
langchain-google-genai>=1.0.0
langchain-community>=0.2.0
langchain-core>=0.2.0
pypdf>=4.0.0
sentence-transformers>=3.0.0
langgraph>=0.1.0
fastapi>=0.110.0
uvicorn>=0.28.0
python-dotenv>=1.0.1

4. Configuration & State Infrastructure
4.1 Global Environment Settings Manager (backend/src/settings.py)
This class encapsulates environment discovery logic. By handling instantiation natively as a singleton instance (settings), individual files can cleanly pull configuration variables programmatically.
# backend/src/settings.py
import os
from dotenv import load_dotenv

# Trace upward to locate the root .env workspace file cleanly
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(dotenv_path=os.path.join(base_dir, ".env"))

class Settings:
    def __init__(self):
        # Google Generative AI (LLM) Settings
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        self.MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.5-flash")

        # Weaviate Hosted Database Clusters
        self.WEAVIATE_URL = os.getenv("WEAVIATE_URL")
        self.WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

        # Auth0 Fine-Grained Authorization Parameter Sets
        self.FGA_STORE_ID = os.getenv("FGA_STORE_ID")
        self.FGA_CLIENT_ID = os.getenv("FGA_CLIENT_ID")
        self.FGA_CLIENT_SECRET = os.getenv("FGA_CLIENT_SECRET")
        self.FGA_API_URL = os.getenv("FGA_API_URL", "[https://api.us1.fga.dev](https://api.us1.fga.dev)")

        # Identity UI & Pipeline Connectors
        self.DEFAULT_DEMO_ROLE = os.getenv("DEFAULT_DEMO_ROLE", "collaborator")
        self.BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/chat")

# Instantiate singleton for centralized use
settings = Settings()

4.2 Initialization & Database Seeding (backend/index_setup.py)
This standalone utility script uses our unified Settings model to parse files, compute vector signatures, populate Weaviate, and register relation schemas with Auth0 FGA.
# backend/index_setup.py
import os
import glob
from src.settings import settings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_weaviate import WeaviateVectorStore
import weaviate
from weaviate.classes.init import Auth
from openfga_sdk import OpenFgaClient, ClientConfiguration, WriteRequest, TupleKey

def get_pdf_chunks(directory_path, role_metadata):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    all_chunks = []
    
    os.makedirs(directory_path, exist_ok=True)
    pdf_files = glob.glob(os.path.join(directory_path, "*.pdf"))
    if not pdf_files:
        print(f"⚠️ No PDF files found in: {directory_path}")
        return all_chunks

    for file_path in pdf_files:
        doc_id = os.path.basename(file_path).replace(".pdf", "").lower().replace(" ", "_")
        print(f"Processing: {file_path} -> ID: doc:{doc_id}")
        
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        chunks = text_splitter.split_documents(docs)
        
        for chunk in chunks:
            chunk.metadata["allowed_role"] = role_metadata
            chunk.metadata["doc_id"] = f"doc:{doc_id}"
            
        all_chunks.extend(chunks)
    return all_chunks

def seed_weaviate(chunks):
    print("Connecting to Hosted Weaviate Cloud Instance...")
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=settings.WEAVIATE_URL,
        auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY)
    )

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    print(f"Uploading {len(chunks)} chunks to Weaviate...")
    vectorstore = WeaviateVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        client=client,
        index_name="DocumentChunk"
    )
    print("✅ Weaviate insertion complete.")
    client.close()

def seed_auth0_fga():
    print("Writing Relation Tuples to Auth0 FGA...")
    config = ClientConfiguration(
        api_url=settings.FGA_API_URL,
        store_id=settings.FGA_STORE_ID,
        client_id=settings.FGA_CLIENT_ID,
        client_secret=settings.FGA_CLIENT_SECRET
    )
    
    tuples = [
        TupleKey(user="user:collaborator", relation="viewer", object="doc:grievance_policy"),
        TupleKey(user="user:admin", relation="viewer", object="doc:grievance_policy"),
        
        TupleKey(user="user:collaborator", relation="viewer", object="doc:whistleblower_policy"),
        TupleKey(user="user:admin", relation="viewer", object="doc:whistleblower_policy"),
        
        TupleKey(user="user:collaborator", relation="viewer", object="doc:terms_and_conditions"),
        TupleKey(user="user:admin", relation="viewer", object="doc:terms_and_conditions"),
        
        TupleKey(user="user:admin", relation="viewer", object="doc:chatbot_takehome_assignment")
    ]
    
    body = WriteRequest(writes=tuples)
    with OpenFgaClient(config) as fga_client:
        fga_client.write(body)
    print("✅ Auth0 FGA configuration complete.")

if __name__ == "__main__":
    public_dir = os.path.join("data", "public")
    private_dir = os.path.join("data", "private")
    
    os.makedirs(public_dir, exist_ok=True)
    os.makedirs(private_dir, exist_ok=True)
    
    print("Loading data catalogs...")
    public_chunks = get_pdf_chunks(public_dir, role_metadata="collaborator")
    private_chunks = get_pdf_chunks(private_dir, role_metadata="admin")
    
    total_chunks = public_chunks + private_chunks
    if total_chunks:
        seed_weaviate(total_chunks)
        seed_auth0_fga()
        print("🎉 Infrastructure initialization complete!")
    else:
        print("❌ Setup halted: Add target files inside backend/data/ routes before executing.")
"""

with open("pr.md", "w", encoding="utf-8") as f:
    f.write(markdown_content)

# Append remaining modular graph scripts refactored with Settings configuration
with open("pr.md", "a", encoding="utf-8") as f:
    f.write("""
## 5. LangGraph Core Engine Implementation

### 5.1 Memory State Engine Schema (`backend/src/state.py`)
```python
# backend/src/state.py
from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    query: str
    current_user: str
    user_role: str
    retrieved_docs: List[Dict[str, Any]]
    generated_response: str
    retry_count: int
    is_valid: bool
    evaluation_feedback: str

5.2 Agent Operations Layer (backend/src/agents.py)
# backend/src/agents.py
from src.settings import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_weaviate import WeaviateVectorStore
from auth0_ai_langchain.fga import FGARetriever
import weaviate
from weaviate.classes.init import Auth

class AgentCluster:
    def __init__(self):
        # Uses explicit references off centralized configuration singleton
        self.llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_NAME,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
    def retrieve_secured_context(self, state):
        print(f"--- RETRIEVER AGENT: Execution checking roles for user:{state['user_role']} ---")
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=settings.WEAVIATE_URL,
            auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY)
        )
        vectorstore = WeaviateVectorStore(
            client=client,
            index_name="DocumentChunk",
            text_key="text",
            embedding=self.embeddings
        )
        
        rewrite_prompt = f"Rewrite this query for semantic document exploration, return ONLY the core terms: {state['query']}"
        rewritten_query = self.llm.invoke(rewrite_prompt).content
        
        fga_retriever = FGARetriever(
            base_retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
            client_id=settings.FGA_CLIENT_ID,
            client_secret=settings.FGA_CLIENT_SECRET,
            store_id=settings.FGA_STORE_ID,
            user_context=lambda inputs: f"user:{state['user_role']}"
        )
        
        raw_docs = fga_retriever.invoke(rewritten_query)
        client.close()
        
        serialized_docs = [{"text": d.page_content, "source": d.metadata.get("doc_id", "unknown")} for d in raw_docs]
        return {"retrieved_docs": serialized_docs, "query": rewritten_query}

    def specialist_synthesis(self, state):
        print("--- SPECIALIST AGENT: Formulating Answer Content ---")
        context_block = "\\n".join([f"[Source: {d['source']}]: {d['text']}" for d in state['retrieved_docs']])
        
        system_prompt = (
            f"You are a strict technical compliance assistant. Answer the user prompt based ONLY on the provided contexts.\\n"
            f"If no explicit matching information is present inside the context details, reply saying you are unauthorized or unable to fetch the answer.\\n"
            f"Context:\\n{context_block}\\n\\n"
            f"User Query: {state['query']}\\n"
            f"Feedback Loop Note: {state.get('evaluation_feedback', 'None')}"
        )
        
        response = self.llm.invoke(system_prompt).content
        return {"generated_response": response}

    def reviewer_verification(self, state):
        print("--- REVIEWER AGENT: Evaluating Assertions Against Original Context ---")
        context_block = "\\n".join([d['text'] for d in state['retrieved_docs']])
        
        evaluation_prompt = (
            f"Critically analyze the generated response against the verified raw text chunks. Identify any hallucinations or assumptions.\\n"
            f"Respond with EXACTLY the word 'VALID' if the generation is perfectly true to the text. Otherwise, output corrections.\\n"
            f"Raw Context:\\n{context_block}\\n"
            f"Generated Response:\\n{state['generated_response']}"
        )
        
        eval_result = self.llm.invoke(evaluation_prompt).content.strip()
        if "VALID" in eval_result:
            return {"is_valid": True, "evaluation_feedback": "", "retry_count": state["retry_count"] + 1}
        else:
            return {"is_valid": False, "evaluation_feedback": eval_result, "retry_count": state["retry_count"] + 1}

5.3 Graph State Network Assembly (backend/src/agent_graph.py)
# backend/src/agent_graph.py
from langgraph.graph import StateGraph, END
from .state import AgentState
from .agents import AgentCluster

cluster = AgentCluster()
workflow = StateGraph(AgentState)

workflow.add_node("retriever", cluster.retrieve_secured_context)
workflow.add_node("specialist", cluster.specialist_synthesis)
workflow.add_node("reviewer", cluster.reviewer_verification)

workflow.set_entry_point("retriever")
workflow.add_edge("retriever", "specialist")
workflow.add_edge("specialist", "reviewer")

def route_evaluation_loop(state):
    if state["is_valid"]:
        print("--> Reviewer Approved Generation Outcome.")
        return "approved"
    elif state["retry_count"] >= 3:
        print("--> System Retry Exhausted. Falling Back Safely.")
        return "halt"
    else:
        print(f"--> Reviewer Flagged Hallucination. Routing back to Specialist. Retry #{state['retry_count']}")
        return "reject"

workflow.add_conditional_edges(
    "reviewer",
    route_evaluation_loop,
    {
        "approved": END,
        "reject": "specialist",
        "halt": END
    }
)

graph = workflow.compile()

6. Pipeline Sandbox Verification (backend/test_graph.py)
Execute this test offline using uv run python test_graph.py before turning on API layers or frontend modules.
# backend/test_graph.py
from src.agent_graph import graph

def run_test_simulation(target_role: str, description: str):
    print(f"\\n=======================================================")
    print(f"RUNNING SECURITY PROFILE TEST: {description} ({target_role})")
    print(f"=======================================================")
    
    mock_payload = {
        "query": "What specific criteria are listed under the chatbot takehome assignment?",
        "current_user": f"test_{target_role}_user",
        "user_role": target_role,
        "retrieved_docs": [],
        "generated_response": "",
        "retry_count": 0,
        "is_valid": False,
        "evaluation_feedback": ""
    }
    
    output = graph.invoke(mock_payload)
    print(f"\\nFinal Execution Result for ({target_role}):")
    print(output["generated_response"])

if __name__ == "__main__":
    run_test_simulation("collaborator", "Expect Total Isolation Block")
    run_test_simulation("admin", "Expect Authorized Elevation Access")

7. Service Gateway Integration (backend/main.py)
# backend/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.agent_graph import graph

app = FastAPI(title="Secure Agentic RAG Endpoint Cluster", version="1.0")

class ChatRequest(BaseModel):
    message: str
    user_id: str
    role: str

@app.post("/api/chat")
async def process_chat_message(payload: ChatRequest):
    try:
        initial_state = {
            "query": payload.message,
            "current_user": payload.user_id,
            "user_role": payload.role,
            "retrieved_docs": [],
            "generated_response": "",
            "retry_count": 0,
            "is_valid": False,
            "evaluation_feedback": ""
        }
        
        result = graph.invoke(initial_state)
        return {"response": result["generated_response"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

8. Client UI Implementation (frontend/app.py)
8.1 Configuration Context (frontend/mock_users.json)
{
  "alice@enterprise.com": {"name": "Alice Sterling", "role": "admin", "id": "user:alice"},
  "bob@enterprise.com": {"name": "Bob Vance", "role": "collaborator", "id": "user:bob"}
}

8.2 Client Dashboard UI (frontend/app.py)
# frontend/app.py
import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

# Frontend reads directly from local env or falls back to backend settings defaults
load_dotenv(dotenv_path="../.env")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/chat")

st.set_page_config(page_title="Agentic RAG Security Sandbox", layout="wide")
st.title("🛡️ Enterprise Agentic RAG Authorization Engine")

with open("mock_users.json", "r") as f:
    users_db = json.load(f)

st.sidebar.header("Identity Access Management (SSO Simulation)")
selected_email = st.sidebar.selectbox("Active Session Login Profile", list(users_db.keys()))
user_profile = users_db[selected_email]

st.sidebar.info(f"**Authenticated Name:** {user_profile['name']}\\n\\n**Assigned FGA Claim Group:** `{user_profile['role']}`")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Query documentation network..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
        
    payload = {
        "message": user_input,
        "user_id": user_profile["id"],
        "role": user_profile["role"]
    }
    
    with st.chat_message("assistant"):
        with st.spinner("Orchestrating agent state sequences..."):
            try:
                res = requests.post(BACKEND_API_URL, json=payload)
                if res.status_code == 200:
                    answer = res.json()["response"]
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error(f"Execution Failure: {res.text}")
            except Exception as e:
                st.error(f"Connection to backend failed: {str(e)}")

9. Fast Execution Verification Pipeline
# Terminal 1: Core Setup and Ingestion
cd backend
uv init --python 3.12
uv add -r requirements.txt
uv run python index_setup.py

# Offline Sandbox Execution Check
uv run python test_graph.py

# Boot Backend Web API Layer
uv run python main.py

# Terminal 2: Boot Streamlit User Interface
cd frontend
uv init --python 3.12
uv add streamlit requests python-dotenv
uv run streamlit run app.py
