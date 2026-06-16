2026-06-15 20:38:27	docker/backend	INFO:     172.19.0.3:33272 - "POST /api/chat HTTP/1.1" 200 OK
2026-06-15 20:38:27	docker/backend
2026-06-15 20:38:27	docker/backend	--- FRONT ROUTER: Classifying Query Intent ---
2026-06-15 20:38:27	docker/backend	Router Decision: CASUAL GREETING
2026-06-15 20:38:27	docker/backend
2026-06-15 20:38:27	docker/backend	--- SPECIALIST AGENT: Formulating Answer Content ---
2026-06-15 20:38:27	docker/backend
2026-06-15 20:38:27	docker/backend	--- REVIEWER AGENT: Evaluating Assertions Against Original Context ---
2026-06-15 20:38:27	docker/backend	Auto-approving non-retrieval response.
2026-06-15 20:38:27	docker/backend	INFO:     172.19.0.3:33272 - "POST /api/chat HTTP/1.1" 200 OK
2026-06-15 20:38:28	docker/backend	INFO:     127.0.0.1:50746 - "GET /health HTTP/1.1" 200 OK
2026-06-15 20:38:28	docker/backend	INFO:     127.0.0.1:50746 - "GET /health HTTP/1.1" 200 OK
2026-06-15 20:38:46	docker/backend	Traceback (most recent call last):
2026-06-15 20:38:46	docker/backend	Traceback (most recent call last):
2026-06-15 20:38:46	docker/backend	  File "/app/backend/main.py", line 43, in process_chat_message
2026-06-15 20:38:46	docker/backend	    result = graph.invoke(initial_state)
2026-06-15 20:38:46	docker/backend	             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-06-15 20:38:46	docker/backend	  File "/usr/local/lib/python3.12/site-packages/langgraph/pregel/__init__.py", line 2844, in invoke
2026-06-15 20:38:46	docker/backend	    for chunk in self.stream(
2026-06-15 20:38:46	docker/backend	                 ^^^^^^^^^^^^
2026-06-15 20:38:46	docker/backend	  File "/usr/local/lib/python3.12/site-packages/langgraph/pregel/__init__.py", line 2534, in stream
2026-06-15 20:38:46	docker/backend	    for _ in runner.tick(
2026-06-15 20:38:46	docker/backend	             ^^^^^^^^^^^^
2026-06-15 20:38:46	docker/backend	  File "/app/backend/src/agents.py", line 165, in retrieve_secured_context
2026-06-15 20:38:46	docker/backend	    retriever=SafeIdRetriever(vectorstore.as_retriever(search_kwargs={"k": 5})),
2026-06-15 20:38:46	docker/backend	INFO:     172.19.0.3:47612 - "POST /api/chat HTTP/1.1" 500 Internal Server Error