import os

# Set longer timeout for HuggingFace downloads
os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '300'


class Config:
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 5000

    # Database connection (same as .NET)
    DB_CONNECTION = "Driver={ODBC Driver 17 for SQL Server};Server=(localdb)\\mssqllocaldb;Database=TalentMarketplace;Trusted_Connection=yes;"

    # ChromaDB settings
    CHROMA_PERSIST_DIR = "./chroma_db"
    COLLECTION_NAME = "employee_skills"

    # SpaCy model
    SPACY_MODEL = "en_core_web_sm"