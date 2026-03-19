"""Стаб RAG pipeline — будет реализован в Фазе 1.

Компоненты:
- embeddings.py: Фабрика embeddings через OpenRouter
- vectorstore.py: Chroma persistent vector store
- loader.py: Загрузчики для .txt .md .pdf .docx .html .csv
- chunker.py: RecursiveCharacterTextSplitter
"""
