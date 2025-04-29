# Science AI Tutor

Science AI Tutor is an intelligent chatbot designed to assist students with NCERT Science curriculum for Class 9 and Class 10. It can answer science-related questions, provide explanations, and track user progress.

## Features

- **NCERT Science Curriculum Support**: Focused on Class 9 and Class 10 NCERT Science topics.
- **General Science Queries**: Capable of answering general science-related questions like "What is science?" or "Explain photosynthesis."
- **Interactive Chat**: Engages users in a conversational manner.
- **Progress Tracking**: Tracks user progress, including total questions asked, correct answers, and accuracy.
- **Polite Greetings**: Responds politely to greetings like "hi", "hello", or "hey".
- **Customizable**: Built with modular components for easy customization.

## How It Works

1. **PDF Data Loading**: Extracts text from PDFs and stores it in a ChromaDB database for retrieval.
2. **Question Answering**: Uses a retrieval-augmented generation (RAG) pipeline to fetch relevant information and generate answers.
3. **Chat History**: Maintains a chat history to provide context-aware responses.
4. **User Progress**: Updates and displays user progress based on interactions.
