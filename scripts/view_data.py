#!/usr/bin/env python3
"""
Script to view all data in the LocalMind project:
- Raw documents
- ChromaDB vector store
- SQLite metadata database
"""

import os
import sqlite3
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATA_DIR = Path("./data")
RAW_FILES_DIR = DATA_DIR / "raw"
CHROMA_PERSIST_DIR = DATA_DIR / "chroma"
SQLITE_PATH = DATA_DIR / "sqlite" / "app.db"


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def view_raw_documents():
    """Display raw documents in data/raw folder."""
    print_section("RAW DOCUMENTS (data/raw/)")
    
    if not RAW_FILES_DIR.exists():
        print("❌ No raw files directory found")
        return
    
    files = [f for f in RAW_FILES_DIR.iterdir() if f.is_file() and f.name != ".gitkeep"]
    
    if not files:
        print("📄 No documents uploaded yet")
        return
    
    print(f"📄 Found {len(files)} document(s):\n")
    for file in files:
        size_mb = file.stat().st_size / (1024 * 1024)
        print(f"  • {file.name}")
        print(f"    Size: {size_mb:.2f} MB")
        print(f"    Type: {file.suffix}")
        print()


def view_chroma_data():
    """Display ChromaDB vector store data."""
    print_section("VECTOR STORE (ChromaDB - data/chroma/)")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(CHROMA_PERSIST_DIR),
            anonymized_telemetry=False,
        )
        client = chromadb.Client(settings)
        collections = client.list_collections()
        
        if not collections:
            print("📦 No collections found")
            return
        
        print(f"📦 Found {len(collections)} collection(s):\n")
        
        for collection in collections:
            print(f"  Collection: {collection.name}")
            count = collection.count()
            print(f"  Total Items: {count}")
            
            if count > 0:
                print(f"  Sample Items (first 3):")
                items = collection.get(limit=3)
                
                for i, (doc_id, metadata, embedding, document) in enumerate(
                    zip(
                        items.get("ids", []),
                        items.get("metadatas", []),
                        items.get("embeddings", []),
                        items.get("documents", []),
                    ),
                    1,
                ):
                    print(f"\n    [{i}] ID: {doc_id}")
                    print(f"        Document: {document[:100]}..." if len(document) > 100 else f"        Document: {document}")
                    print(f"        Metadata: {metadata}")
                    if embedding:
                        print(f"        Embedding Size: {len(embedding)} dimensions")
            
            print()
    
    except Exception as e:
        print(f"❌ Error reading ChromaDB: {e}")


def view_sqlite_data():
    """Display SQLite database content."""
    print_section("METADATA DATABASE (SQLite - data/sqlite/app.db)")
    
    if not SQLITE_PATH.exists():
        print("❌ SQLite database not found")
        return
    
    try:
        conn = sqlite3.connect(SQLITE_PATH)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        if not tables:
            print("📋 No tables found in database")
            conn.close()
            return
        
        print(f"📋 Found {len(tables)} table(s):\n")
        
        for (table_name,) in tables:
            print(f"  Table: {table_name}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"  Rows: {count}")
            
            # Get column info
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            print(f"  Columns: {', '.join([col[1] for col in columns])}")
            
            # Get sample data
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
                rows = cursor.fetchall()
                print(f"  Sample Data (first 3 rows):")
                
                for row in rows:
                    print(f"    {row}")
            
            print()
        
        conn.close()
    
    except Exception as e:
        print(f"❌ Error reading SQLite: {e}")


def view_summary():
    """Display overall summary."""
    print_section("DATA SUMMARY")
    
    # Raw files count
    raw_count = 0
    raw_size = 0
    if RAW_FILES_DIR.exists():
        for f in RAW_FILES_DIR.iterdir():
            if f.is_file() and f.name != ".gitkeep":
                raw_count += 1
                raw_size += f.stat().st_size
    
    # Chroma size
    chroma_size = 0
    if CHROMA_PERSIST_DIR.exists():
        for f in CHROMA_PERSIST_DIR.rglob("*"):
            if f.is_file():
                chroma_size += f.stat().st_size
    
    # SQLite size
    sqlite_size = 0
    if SQLITE_PATH.exists():
        sqlite_size = SQLITE_PATH.stat().st_size
    
    print(f"📄 Raw Documents: {raw_count} file(s) ({raw_size / (1024*1024):.2f} MB)")
    print(f"📦 Vector Store: {chroma_size / (1024*1024):.2f} MB")
    print(f"📋 SQLite DB: {sqlite_size / 1024:.2f} KB")
    print(f"\n💾 Total Data Size: {(raw_size + chroma_size + sqlite_size) / (1024*1024):.2f} MB")


if __name__ == "__main__":
    print("\n🔍 LOCALMIND DATA VIEWER")
    
    view_raw_documents()
    view_chroma_data()
    view_sqlite_data()
    view_summary()
    
    print_section("Done")
    print()
