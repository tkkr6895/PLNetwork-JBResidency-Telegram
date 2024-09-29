from langchain.document_loaders import TextLoader, PyPDFLoader, CSVLoader
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import os

# Path to the directory containing your documents
DOCUMENTS_PATH = os.getcwd()

# Initialize SentenceTransformer embeddings using the 'all-MiniLM-L6-v2' model
embedding_model = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')

# Load documents
documents = []
for filename in os.listdir(DOCUMENTS_PATH):
    file_path = os.path.join(DOCUMENTS_PATH, filename)
    if filename.endswith(".txt"):
        loader = TextLoader(file_path)
    elif filename.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif filename.endswith(".csv"):
        loader = CSVLoader(file_path)  # Load CSV files
    else:
        continue  # Skip unsupported file types
    documents.extend(loader.load())

# Create the FAISS Vector Store (Knowledge Base)
vector_store = FAISS.from_documents(documents, embedding_model)

# Save the Vector Store Locally
vector_store.save_local("faiss_index")

print("Knowledge base created and saved successfully.")