"""
Pipeline RAG do BluaDiagnostics.

Fluxo:
1. build_vectorstore(): roda UMA vez para indexar a knowledge_base
   - carrega os .md de data/knowledge_base/
   - quebra em chunks de ~500 caracteres
   - gera embeddings com Google (models/text-embedding-004)
   - persiste no ChromaDB em data/chroma_db/

2. retrieve(query, k): usado pelos agentes em runtime
   - busca os k chunks mais relevantes para a query
   - retorna lista de {fonte, conteudo}

Para popular o vector store, rode UMA VEZ:
    python src/rag/pipeline.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma


# ─── Configuração ─────────────────────────────────────────────

load_dotenv()  # carrega GOOGLE_API_KEY do .env

# Caminhos absolutos a partir da raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parents[2]
KB_PATH = PROJECT_ROOT / "data" / "knowledge_base"
CHROMA_PATH = PROJECT_ROOT / "data" / "chroma_db"

# Parâmetros do RAG
CHUNK_SIZE = 500          # caracteres por chunk
CHUNK_OVERLAP = 50        # sobreposição entre chunks (mantém contexto)
EMBEDDING_MODEL = "gemini-embedding-001"  # Google, gratuito
COLLECTION_NAME = "blua_knowledge_base"


def _get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Cria instância de embeddings do Google. Valida a chave."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY não encontrada. "
            "Configure no arquivo .env na raiz do projeto."
        )
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=api_key,
    )


# ─── 1. Construção do vector store (rodar uma vez) ────────────

def build_vectorstore() -> Chroma:
    """
    Carrega os documentos da knowledge_base, quebra em chunks,
    gera embeddings e persiste no ChromaDB.
    """
    print(f"Carregando documentos de {KB_PATH}...")

    if not KB_PATH.exists():
        raise FileNotFoundError(f"Diretório não encontrado: {KB_PATH}")

    loader = DirectoryLoader(
        str(KB_PATH),
        glob="*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()

    if not docs:
        raise ValueError(f"Nenhum .md encontrado em {KB_PATH}")

    print(f"  {len(docs)} documentos carregados:")
    for d in docs:
        nome = Path(d.metadata["source"]).name
        print(f"    - {nome} ({len(d.page_content)} caracteres)")

    # Chunking
    print(f"\nQuebrando em chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"  {len(chunks)} chunks gerados")

    # Embeddings + ChromaDB
    print(f"\nGerando embeddings com {EMBEDDING_MODEL}...")
    embeddings = _get_embeddings()

    # Se já existe um vector store, remove para reindexar do zero
    if CHROMA_PATH.exists():
        import shutil
        print(f"  Removendo vector store antigo em {CHROMA_PATH}...")
        shutil.rmtree(CHROMA_PATH)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PATH),
        collection_name=COLLECTION_NAME,
    )

    print(f"\n✓ Vector store criado em {CHROMA_PATH}")
    print(f"  Total de chunks indexados: {vectorstore._collection.count()}")
    return vectorstore


# ─── 2. Retriever (usado pelos agentes) ───────────────────────

_vectorstore_cache = None


def _get_vectorstore() -> Chroma:
    """Carrega o vector store persistido. Cacheia para performance."""
    global _vectorstore_cache
    if _vectorstore_cache is not None:
        return _vectorstore_cache

    if not CHROMA_PATH.exists():
        raise FileNotFoundError(
            f"Vector store não encontrado em {CHROMA_PATH}. "
            "Execute primeiro: python src/rag/pipeline.py"
        )

    _vectorstore_cache = Chroma(
        persist_directory=str(CHROMA_PATH),
        embedding_function=_get_embeddings(),
        collection_name=COLLECTION_NAME,
    )
    return _vectorstore_cache


def retrieve(query: str, k: int = 3) -> list[dict]:
    """
    Busca os k chunks mais relevantes para a query.

    Retorna lista de dicts com:
    - fonte: nome do arquivo de origem
    - conteudo: texto do chunk
    - score: distância (menor = mais relevante)
    """
    vs = _get_vectorstore()
    docs_com_score = vs.similarity_search_with_score(query, k=k)

    return [
        {
            "fonte": Path(doc.metadata.get("source", "desconhecido")).name,
            "conteudo": doc.page_content,
            "score": float(score),
        }
        for doc, score in docs_com_score
    ]


# ─── 3. Teste rápido ──────────────────────────────────────────

if __name__ == "__main__":
    # Etapa 1: construir o vector store
    build_vectorstore()

    # Etapa 2: testar retrieval com queries clínicas
    print("\n" + "=" * 60)
    print("TESTES DE RETRIEVAL")
    print("=" * 60)

    queries_teste = [
        "Estou com dor no peito irradiando pro braço esquerdo",
        "Posso tomar ibuprofeno com losartana?",
        "Como agendar uma teleconsulta no Blua?",
        "Qual a meta de pressão para diabético?",
        "O que o BluaCheck pode fazer?",
    ]

    for query in queries_teste:
        print(f"\n[QUERY] {query}")
        resultados = retrieve(query, k=2)
        for i, r in enumerate(resultados, 1):
            preview = r["conteudo"][:120].replace("\n", " ")
            print(f"  [{i}] {r['fonte']} (score={r['score']:.3f})")
            print(f"      \"{preview}...\"")
