# Updating the architecture diagram

Here is the step-by-step description of your final architecture diagram, tracing a user request from the initial login simulation down through your secure multi-agent graph and back.

## Phase 1: User Identity & Gateway (Steps 1–4)
1. SSO Login: The user authenticates through a Single Sign-On simulation (mapped via your simulated database configuration) to establish their unique profile.
2. RBAC/ABAC Claims Execution: The authentication system returns security claims detailing the active user's roles (admin or collaborator) back to the client interface.
3. Query Submission: The user submits a plain-text prompt (e.g., asking about a policy or a casual greeting) directly into the Static Web App interface.
4. Secure Context Injection: The Static Web App passes the raw user prompt along with the cryptographic identity and RBAC/ABAC claims down as a structural request payload into the FastAPI application running inside the Container Web App.

## Phase 2: Intent Analysis & Pre-Filtering (Steps 4.1–4.2)
4.1. The Front Agent Guardrail: The request lands immediately on the Front Agent. This router node processes the incoming string using fast, deterministic logic to evaluate whether the prompt is relevant to hirebooth.com or casual banter. • Off-Topic Switch (Step 4.1 / 10.2): If the query is flagged as completely off-topic, it triggers an immediate branch. The system crafts a hardcoded template fallback response without consuming LLM tokens, passing data to Weaviate, or invoking Auth0 FGA, routing the execution instantly back to the web application interface.
4.2. Intent Approval: If the prompt passes verification as a valid, on-topic policy or documentation query (or a standard conversational greeting), the state passes forward cleanly to the core RAG processor pipeline.

## Phase 3: Secure Context Retrieval & Authorization (Steps 5–7)
5. Query Rewriting: The Retriever Agent receives the payload and executes a semantic rewrite prompt via Gemini, distilling the user's intent down into pure keywords optimized for vector matching. This optimized search vector is sent over to the RAG Pipeline.
6. Vector Store Context Fetch: The rewritten terms hit your hosted Weaviate Vector Store. Weaviate calculates nearest-neighbor similarities across the embedded document chunks and pulls raw matching segments sourced from Blob Storage.
7. Fine-Grained Authorization Interception: Instead of returning those raw chunks blindly to the LLM, they are intercepted by the FGA Retriever middleware. The filter maps the user's active role context against specific resource tuples. Unauthorized document fragments are scrubbed from the stream entirely, and only authenticated, Filtered Docs are returned to the active runtime state.

## Phase 4: Synthesis, Quality Control, & Exit (Steps 8–11)
8. Prompt Augmentation: The authorized text chunks are structured into a clean, context-grounded payload and sent directly to the Specialist Agent.
9. Response Synthesis: The Specialist Agent analyzes the strict bounds of the text and generates a comprehensive compliance response based exclusively on the facts present.
10. The Reviewer Evaluation Gate: The response is evaluated by the Reviewer Agent. • Self-Healing Rejection Loop (Step 10.1): If the Reviewer detects a hallucination, unverified inference, or mismatch against the raw facts, it marks the state as invalid, writes corrections to the state metadata, and loops back to the Specialist Agent for enhancement (up to 3 total retries).
11. Final Response Delivery: Once the Reviewer validates the answer text as factual (or the safety timeout counter expires), the loop breaks. The finalized, secure response drops down out of the Container Web App layer and surfaces on the user's screen.