import os
import glob
import weaviate
from weaviate.classes.init import Auth
from openfga_sdk import (
    ClientConfiguration,
    WriteAuthorizationModelRequest,
    TypeDefinition,
    Userset,
    Metadata,
    RelationMetadata,
    RelationReference,
    CreateStoreRequest
)
from openfga_sdk.sync import OpenFgaClient
from openfga_sdk.client.models import ClientWriteRequest
from openfga_sdk.client.models import ClientTuple
from openfga_sdk.credentials import Credentials, CredentialConfiguration
from src.settings import settings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_weaviate import WeaviateVectorStore

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
        return weaviate.connect_to_local(
            host=host,
            port=port,
            additional_config=additional_config,
            skip_init_checks=True
        )

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
            # Clean metadata to avoid schema/type mapping errors in Weaviate
            chunk.metadata = {
                "allowed_role": role_metadata,
                "doc_id": f"doc:{doc_id}",
                "source": os.path.basename(file_path)
            }
            
        all_chunks.extend(chunks)
    return all_chunks

def seed_weaviate(chunks):
    client = get_weaviate_client()
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
    print("Writing Relation Tuples and Authorization Model to Auth0 FGA / OpenFGA...")
    
    # 1. Check if we need to create a store locally (if FGA_STORE_ID is empty)
    if not settings.FGA_STORE_ID:
        print("No FGA_STORE_ID configured. Creating a new local store...")
        temp_config = get_fga_config(store_id="")
        with OpenFgaClient(temp_config) as temp_client:
            store_response = temp_client.create_store(CreateStoreRequest(name="agentic-rag-demo"))
            settings.FGA_STORE_ID = store_response.id
            print(f"✅ Local store created. Store ID: {settings.FGA_STORE_ID}")

    config = get_fga_config()
    with OpenFgaClient(config) as fga_client:
        # 2. Write the Authorization Model first
        model_request = WriteAuthorizationModelRequest(
            schema_version="1.1",
            type_definitions=[
                TypeDefinition(type="user"),
                TypeDefinition(
                    type="doc",
                    relations={
                        "viewer": Userset(this={})
                    },
                    metadata=Metadata(
                        relations={
                            "viewer": RelationMetadata(
                                directly_related_user_types=[
                                    RelationReference(type="user")
                                ]
                            )
                        }
                    )
                )
            ]
        )
        print("Writing Authorization Model...")
        model_response = fga_client.write_authorization_model(model_request)
        print(f"✅ Authorization Model written. ID: {model_response.authorization_model_id}")

        # 3. Seed relationship tuples
        tuples = [
            ClientTuple(user="user:collaborator", relation="viewer", object="doc:grievance_policy"),
            ClientTuple(user="user:admin", relation="viewer", object="doc:grievance_policy"),
            
            ClientTuple(user="user:collaborator", relation="viewer", object="doc:whistleblower_policy"),
            ClientTuple(user="user:admin", relation="viewer", object="doc:whistleblower_policy"),
            
            ClientTuple(user="user:collaborator", relation="viewer", object="doc:terms_and_conditions"),
            ClientTuple(user="user:admin", relation="viewer", object="doc:terms_and_conditions"),

            ClientTuple(user="user:collaborator", relation="viewer", object="doc:service_guide"),
            ClientTuple(user="user:admin", relation="viewer", object="doc:service_guide"),
            
            ClientTuple(user="user:admin", relation="viewer", object="doc:chatbot_takehome_assignment")
        ]
        
        body = ClientWriteRequest(writes=tuples)
        print("Writing tuples...")
        fga_client.write(body)
        print("✅ Auth0 FGA / OpenFGA tuples configuration complete.")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    public_dir = os.path.join(script_dir, "data", "public")
    private_dir = os.path.join(script_dir, "data", "private")
    
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
        print(f"\n👉 IMPORTANT: Add this to your root .env file if running locally:\nFGA_STORE_ID=\"{settings.FGA_STORE_ID}\"\n")
    else:
        print("❌ Setup halted: Add target files inside backend/data/ routes before executing.")
