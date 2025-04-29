import os
import fitz  # PyMuPDF for extracting text from PDF
from dotenv import load_dotenv
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from user_data import user_data
from concurrent.futures import ThreadPoolExecutor

# Load environment variables from .env
load_dotenv()

# Define the persistent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
persistent_directory = os.path.join(current_dir, "db", "chroma_db_with_metadata")

# Define the embedding model
embeddings = GoogleGenerativeAIEmbeddings(model='models/text-embedding-004')

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join([page.get_text("text") for page in doc])
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""

# Function to load multiple PDFs from a folder into ChromaDB
def load_pdfs_from_folder(folder_path):
    all_docs = []
    total_pdfs = 0

    def process_pdf(pdf_path, relative_path):
        nonlocal total_pdfs
        text = extract_text_from_pdf(pdf_path)
        if text:
            all_docs.append(Document(
                page_content=text,
                metadata={
                    "source": relative_path,
                    "filename": os.path.basename(pdf_path)
                }
            ))
            total_pdfs += 1
            print(f"Loaded: {relative_path}")

    def scan_directory(current_path, relative_path=""):
        pdf_files = []
        for item in os.listdir(current_path):
            item_path = os.path.join(current_path, item)
            item_relative_path = os.path.join(relative_path, item)
            if os.path.isfile(item_path) and item.lower().endswith('.pdf'):
                pdf_files.append((item_path, item_relative_path))
            elif os.path.isdir(item_path):
                scan_directory(item_path, item_relative_path)
        return pdf_files

    print(f"\nScanning for PDFs in: {folder_path}")
    pdf_files = scan_directory(folder_path)

    with ThreadPoolExecutor() as executor:
        for pdf_path, relative_path in pdf_files:
            executor.submit(process_pdf, pdf_path, relative_path)

    if all_docs:
        print(f"\nFound {total_pdfs} PDFs. Creating ChromaDB...")
        db = Chroma.from_documents(all_docs, embedding=embeddings, persist_directory=persistent_directory)
        db._persist_directory = persistent_directory  # Ensure persistence
        print(f"Successfully loaded {len(all_docs)} PDFs into ChromaDB.")
    else:
        print("No PDFs found in the folder or its subdirectories.")

# Function to load PDFs only if database doesn't exist
def initialize_database():
    if not os.path.exists(persistent_directory) or not os.listdir(persistent_directory):
        print("🔹 Initializing database...")
        pdf_folder = "pdf_data"
        if os.path.exists(pdf_folder):
            load_pdfs_from_folder(pdf_folder)
        else:
            print(f"Warning: PDF folder '{pdf_folder}' not found!")
    
    return Chroma(persist_directory=persistent_directory, embedding_function=embeddings)

# Initialize database once at startup
db = initialize_database()

# Configure retriever with optimal settings
retriever = db.as_retriever(
    search_type="similarity",
    search_kwargs={
        "k": 2,  # Reduced from 3 to 2 for faster retrieval
        "filter": None
    }
)

# Define LLM model
llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash', temperature=0, max_tokens=256, max_retries=2)

# Contextualize question prompt
contextualize_q_prompt = ChatPromptTemplate.from_messages([
    ("system", "Given a chat history and the latest user question, reformulate a standalone question."),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

# Create history-aware retriever
history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

# Answer question prompt
qa_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "You are SciTutor, an AI science tutor for NCERT Science curriculum for Class 9 and 10. "
     "Answer science-related questions clearly and concisely. "
     "Context for this interaction:\n{context}"
    ),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

# Create document processing chain
question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

def display_progress(username):
    progress = user_data.get_progress(username)
    if progress:
        print("\n=== Your Learning Progress ===")
        print(f"Username: {progress['username']}")
        print(f"Total Questions Asked: {progress['total_questions']}")
        print(f"Correct Answers: {progress['correct_answers']}")
        print(f"Accuracy: {progress['accuracy']:.1f}%")
        print("\nTopics Covered:")
        for topic in progress['topics_covered']:
            print(f"- {topic}")
        print(f"\nLast Session: {progress['last_session']}")
    else:
        print("No progress data found.")

# Function to start the chatbot
def continual_chat():
    print("Welcome to Science AI Tutor!")
    username = input("Please enter your username: ")
    user_data.create_user(username)
    
    print("\nStart chatting! Type 'exit' to end, 'progress' to see your learning progress.")
    chat_history = []
    
    while True:
        query = input("\nYou: ").strip().lower()
        
        # Handle greetings
        if query in ["hi", "hello", "hey", "greetings"]:
            print("AI: Hello there! I am your SciTutor. How may I help you today?")
            continue
        
        if query == "exit":
            break
        elif query == "progress":
            display_progress(username)
            continue
            
        # Store user message
        user_data.update_chat_history(username, query, True)
        
        result = rag_chain.invoke({"input": query, "chat_history": chat_history[-20:]})  # Limit chat history to last 20 messages
        print(f"AI: {result['answer']}")
        
        # Store AI response
        user_data.update_chat_history(username, result['answer'], False)
        
        # Update progress (you might want to add logic to determine if the answer was correct)
        user_data.update_progress(username, "General Science", True)  # Replace with actual topic detection
        
        chat_history.append(HumanMessage(content=query))
        chat_history.append(AIMessage(content=result["answer"]))

if __name__ == "__main__":
    continual_chat()
