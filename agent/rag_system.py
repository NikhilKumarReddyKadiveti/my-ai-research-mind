import chromadb
from sentence_transformers import SentenceTransformer
import uuid

class RAGSystem:
    """
    Retrieval-Augmented Generation System.
    Stores scraped data in a vector database and retrieves relevant chunks for reasoning.
    """
    def __init__(self, collection_name="research_docs"):
        # Initialize the embedding model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path="researchmind-ai/agent/vector_db")
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, documents, metadatas=None):
        """
        Add documents to the vector database.
        documents: List of strings
        metadatas: List of dictionaries
        """
        ids = [str(uuid.uuid4()) for _ in range(len(documents))]
        
        # Chroma handles embedding generation automatically if we provide a function,
        # but here we generate them manually using SentenceTransformers for more control.
        embeddings = self.model.encode(documents).tolist()
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        print(f"Added {len(documents)} document chunks to the RAG system.")

    def query(self, query_text, n_results=3):
        """Retrieve relevant document chunks for a query."""
        query_embedding = self.model.encode([query_text]).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        return results

if __name__ == "__main__":
    # Quick test
    rag = RAGSystem()
    sample_docs = [
        "The Transformer model uses attention mechanisms to process sequences.",
        "PyTorch is a popular deep learning framework.",
        "A Small Language Model (SLM) is more efficient than a Large Language Model (LLM)."
    ]
    rag.add_documents(sample_docs, metadatas=[{"source": "test"}] * 3)
    
    res = rag.query("What is an SLM?")
    print(f"Query Result: {res['documents'][0][0]}")
