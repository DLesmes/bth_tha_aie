from src.settings import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_weaviate import WeaviateVectorStore
from auth0_ai_langchain import FGARetriever
from openfga_sdk import ClientConfiguration
from openfga_sdk.client.models import ClientBatchCheckItem
from openfga_sdk.credentials import Credentials, CredentialConfiguration
from langchain.schema import BaseRetriever, Document
from pydantic import PrivateAttr
import weaviate
from weaviate.classes.init import Auth


class SafeIdRetriever(BaseRetriever):
    """Wrap a retriever and ensure each Document has a stable id for FGA checks."""

    _base_retriever: BaseRetriever = PrivateAttr()

    def __init__(self, base_retriever: BaseRetriever):
        super().__init__()
        self._base_retriever = base_retriever

    def _normalize_ids(self, docs: list[Document]) -> list[Document]:
        for doc in docs:
            if not getattr(doc, "id", None):
                doc.id = doc.metadata.get("doc_id") if isinstance(doc.metadata, dict) else None
        return docs

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        docs = self._base_retriever._get_relevant_documents(query, run_manager=run_manager)
        return self._normalize_ids(docs)

    async def _aget_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        docs = await self._base_retriever._aget_relevant_documents(query, run_manager=run_manager)
        return self._normalize_ids(docs)

def get_weaviate_client():
    url = settings.WEAVIATE_URL
    init_timeout = 30
    additional_config = weaviate.config.AdditionalConfig(
        timeout=weaviate.config.Timeout(init=init_timeout)
    )

    if not url:
        print("Using default local Weaviate client...")
        return weaviate.connect_to_local(
            port=8050,
            additional_config=additional_config,
            skip_init_checks=True
        )
    
    if "weaviate.network" in url or "aws.weaviate.cloud" in url:
        print(f"Connecting to Weaviate Cloud: {url}")
        return weaviate.connect_to_weaviate_cloud(
            cluster_url=url,
            auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
            additional_config=additional_config,
            skip_init_checks=True
        )
    else:
        # Local or custom URL
        host = "localhost"
        port = 8080
        if "://" in url:
            netloc = url.split("://")[1]
        else:
            netloc = url
        if ":" in netloc:
            host, port_str = netloc.split(":")
            port = int(port_str.split("/")[0])
        else:
            host = netloc
        
        print(f"Connecting to Local Weaviate: host={host}, port={port}")
        return weaviate.connect_to_local(host=host, port=port)

def get_fga_config(store_id=None):
    api_url = settings.FGA_API_URL or "http://localhost:8081"
    credentials = None

    if settings.FGA_CLIENT_ID and settings.FGA_CLIENT_SECRET and settings.FGA_API_AUDIENCE and settings.FGA_API_ISSUER:
        credentials = Credentials(
            method='client_credentials',
            configuration=CredentialConfiguration(
                client_id=settings.FGA_CLIENT_ID,
                client_secret=settings.FGA_CLIENT_SECRET,
                api_audience=settings.FGA_API_AUDIENCE,
                api_issuer=settings.FGA_API_ISSUER
            )
        )
    elif settings.FGA_API_TOKEN:
        credentials = Credentials(
            method='api_token',
            configuration=CredentialConfiguration(
                api_token=settings.FGA_API_TOKEN
            )
        )

    return ClientConfiguration(
        api_url=api_url,
        store_id=store_id or settings.FGA_STORE_ID,
        credentials=credentials
    )

class AgentCluster:
    def __init__(self):
        # Initialize Google Gemini via langchain-google-genai
        self.llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_NAME,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    def front_router(self, state):
        print(f"\n--- FRONT ROUTER: Classifying Query Intent ---")
        query_lower = state['query'].strip().lower()

        # 1. Deterministic Off-Topic Rule (No LLM Call)
        booth_keywords = ["booth", "hirebooth", "policy", "grievance", "whistleblower", "terms", "condition", "assignment", "chatbot"]
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "hola"]
        goodbyes = ["bye", "goodbye", "see ya", "adios", "thank you", "thanks"]
        
        is_greeting = any(word == query_lower for word in greetings)
        is_goodbye = any(word == query_lower for word in goodbyes)
        
        if is_greeting:
            print("Router Decision: CASUAL GREETING")
            return {"evaluation_feedback": "casual_greeting"}
            
        if is_goodbye:
            print("Router Decision: CASUAL GOODBYE")
            return {"evaluation_feedback": "casual_goodbye"}

        has_booth_context = any(keyword in query_lower for keyword in booth_keywords)
        
        if not has_booth_context:
            print("Router Decision: DETERMINISTIC OFF-TOPIC BLOCK (NO LLM)")
            response = "I am a dedicated compliance assistant for HireBooth. I can only assist with topics related to our corporate policies, terms, and assignments. Please let me know if you have any questions regarding those areas."
            return {
                "generated_response": response,
                "evaluation_feedback": "off_topic"
            }

        print("Router Decision: REQUIRES RAG RETRIEVAL")
        return {"evaluation_feedback": "requires_retrieval"}
        
    def retrieve_secured_context(self, state):
        print(f"\n--- RETRIEVER AGENT: Checking roles for user:{state['current_user']} with role:{state['user_role']} ---")
        
        client = get_weaviate_client()
        vectorstore = WeaviateVectorStore(
            client=client,
            index_name="DocumentChunk",
            text_key="text",
            embedding=self.embeddings
        )
        
        rewrite_prompt = f"Rewrite this query for semantic document exploration, return ONLY the core terms: {state['query']}"
        rewritten_query = self.llm.invoke(rewrite_prompt).content.strip()
        print(f"Rewritten Query: '{rewritten_query}'")
        
        # Setup OpenFGA client configuration using the helper
        config = get_fga_config()
        
        # Wrap vector store retriever with Auth0 FGARetriever
        fga_retriever = FGARetriever(
            retriever=SafeIdRetriever(vectorstore.as_retriever(search_kwargs={"k": 5})),
            build_query=lambda doc: ClientBatchCheckItem(
                user=f"user:{state['user_role']}",
                relation="viewer",
                object=doc.metadata.get("doc_id", "unknown")
            ),
            fga_configuration=config
        )
        
        print(f"Invoking secure FGA retriever for user:{state['user_role']}...")
        raw_docs = fga_retriever.invoke(rewritten_query)
        client.close()
        
        serialized_docs = [{"text": d.page_content, "source": d.metadata.get("doc_id", "unknown")} for d in raw_docs]
        print(f"Retrieved and Authorized {len(serialized_docs)} documents.")
        return {"retrieved_docs": serialized_docs, "query": rewritten_query}

    def specialist_synthesis(self, state):
        print("\n--- SPECIALIST AGENT: Formulating Answer Content ---")
        
        router_flag = state.get('evaluation_feedback', 'None')
        
        if router_flag == "casual_greeting":
            response = "Hello! I am your HireBooth compliance assistant. How can I help you with our corporate policies or documentation today?"
            return {"generated_response": response}
            
        if router_flag == "casual_goodbye":
            response = "Goodbye! Feel free to reach out if you have any more questions about HireBooth policies. Have a great day!"
            return {"generated_response": response}

        if not state['retrieved_docs']:
            print("No authorized documents found in state.")
            response = "I am sorry, but you are not authorized to view the documents required to answer this query, or no matching documentation was found."
            return {"generated_response": response}
            
        context_block = "\n".join([f"[Source: {d['source']}]: {d['text']}" for d in state['retrieved_docs']])
        
        system_prompt = (
            f"You are a strict technical compliance assistant for HireBooth. Answer the user prompt based ONLY on the provided contexts.\n"
            f"If no explicit matching information is present inside the context details, reply saying you are unauthorized or unable to fetch the answer.\n"
            f"Context:\n{context_block}\n\n"
            f"User Query: {state['query']}\n"
            f"Feedback Loop Note: {state.get('evaluation_feedback', 'None')}"
        )
        
        response = self.llm.invoke(system_prompt).content
        return {"generated_response": response}

    def reviewer_verification(self, state):
        print("\n--- REVIEWER AGENT: Evaluating Assertions Against Original Context ---")
        
        router_flag = state.get('evaluation_feedback', 'None')
        if router_flag in ["casual_greeting", "casual_goodbye", "off_topic"]:
            print("Auto-approving non-retrieval response.")
            return {"is_valid": True, "evaluation_feedback": router_flag, "retry_count": state["retry_count"] + 1}
        
        # If no documents were retrieved, it is automatically valid (fallback refusal is safe)
        if not state['retrieved_docs']:
            print("No retrieved documents. Auto-approving safe refusal response.")
            return {"is_valid": True, "evaluation_feedback": "", "retry_count": state["retry_count"] + 1}
            
        context_block = "\n".join([d['text'] for d in state['retrieved_docs']])
        
        evaluation_prompt = (
            f"Critically analyze the generated response against the verified raw text chunks. Identify any hallucinations or assumptions.\n"
            f"Respond with EXACTLY the word 'VALID' if the generation is perfectly true to the text. Otherwise, output corrections.\n"
            f"Raw Context:\n{context_block}\n"
            f"Generated Response:\n{state['generated_response']}"
        )
        
        eval_result = self.llm.invoke(evaluation_prompt).content.strip()
        print(f"Reviewer Evaluation: '{eval_result}'")
        
        if "VALID" in eval_result:
            print("Reviewer Decision: APPROVED")
            return {"is_valid": True, "evaluation_feedback": "", "retry_count": state["retry_count"] + 1}
        else:
            print("Reviewer Decision: REJECTED")
            return {"is_valid": False, "evaluation_feedback": eval_result, "retry_count": state["retry_count"] + 1}
