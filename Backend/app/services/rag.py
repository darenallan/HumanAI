"""
rag.py
------
Service RAG (Retrieval-Augmented Generation)
  - Ingestion documentaire (PDF, DOCX)
  - Découpage en chunks
  - Embedding (OpenAI)
  - Recherche par similarité (Cosinus sur pgvector / JSONB)
  - Chat sémantique avec détection des requêtes sensibles
"""
import io
import math
import logging
import uuid
import tiktoken
from pypdf import PdfReader
from docx import Document
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import settings
from app.models.rag import RAGDocument, RAGChunk, RAGDocumentAccess
from app.models.enums import RAGSourceTypeEnum, RoleEnum

logger = logging.getLogger(__name__)

# OpenAI Client
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


# ─── EXTRACTION & CHUNKING ────────────────────────────────────────────────────

async def extract_text(file_bytes: bytes, filename: str) -> tuple[str, RAGSourceTypeEnum]:
    """Extrait le texte d'un PDF ou DOCX et détermine la catégorie sémantique."""
    ext = filename.split(".")[-1].lower()
    text = ""
    
    # Détermination de la catégorie sémantique de source
    filename_lower = filename.lower()
    if "reglement" in filename_lower or "policy" in filename_lower or "charte" in filename_lower:
        source_type = RAGSourceTypeEnum.POLICY
    elif "guide" in filename_lower:
        source_type = RAGSourceTypeEnum.GUIDE
    elif "convention" in filename_lower:
        source_type = RAGSourceTypeEnum.CONVENTION
    elif "procedure" in filename_lower:
        source_type = RAGSourceTypeEnum.PROCEDURE
    elif "faq" in filename_lower:
        source_type = RAGSourceTypeEnum.FAQ
    else:
        source_type = RAGSourceTypeEnum.GUIDE
    
    try:
        if ext == "pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif ext in ["docx", "doc"]:
            doc = Document(io.BytesIO(file_bytes))
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif ext in ["txt", "md"]:
            text = file_bytes.decode("utf-8")
        else:
            raise ValueError(f"Format non supporté: {ext}")
            
        return text.strip(), source_type
    except Exception as e:
        logger.error(f"Erreur extraction document {filename}: {e}")
        raise ValueError("Impossible d'extraire le texte du document.")


def chunk_text(text: str, max_tokens: int = 400) -> list[str]:
    """Découpe un texte long en chunks de taille maximale (tokens)."""
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text)
        
    return chunks


# ─── EMBEDDINGS & SIMILARITY ──────────────────────────────────────────────────

async def get_embedding(text: str) -> list[float]:
    """Génère un embedding vectoriel via l'API OpenAI (ou mock déterministe en DEBUG)."""
    import hashlib
    import random

    is_placeholder = (
        not settings.OPENAI_API_KEY
        or settings.OPENAI_API_KEY.startswith("sk-proj-xxx")
        or "change" in settings.OPENAI_API_KEY.lower()
    )

    if is_placeholder and settings.DEBUG:
        # Générateur d'embedding déterministe pour le mode de développement/tests
        h = hashlib.sha256(text.encode("utf-8")).digest()
        rng = random.Random(h)
        mock_vector = [rng.uniform(-1.0, 1.0) for _ in range(1536)]
        norm = math.sqrt(sum(x*x for x in mock_vector))
        if norm > 0:
            mock_vector = [x / norm for x in mock_vector]
        return mock_vector

    try:
        response = await openai_client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Erreur API OpenAI Embedding: {e}")
        if settings.DEBUG:
            logger.warning("Fallback sur l'embedding mock déterministe en raison d'une erreur API.")
            h = hashlib.sha256(text.encode("utf-8")).digest()
            rng = random.Random(h)
            mock_vector = [rng.uniform(-1.0, 1.0) for _ in range(1536)]
            norm = math.sqrt(sum(x*x for x in mock_vector))
            if norm > 0:
                mock_vector = [x / norm for x in mock_vector]
            return mock_vector
        raise ValueError("Erreur lors de la génération de l'embedding.")


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calcule la similarité cosinus entre deux vecteurs (fallback local)."""
    if not vec1 or not vec2:
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


# ─── INGESTION & RECHERCHE ────────────────────────────────────────────────────

async def ingest_document(
    db: AsyncSession, 
    title: str, 
    file_bytes: bytes, 
    filename: str, 
    allowed_roles: list[RoleEnum]
) -> RAGDocument:
    """Ingère un document : extraction, chunking, embedding, et persistance."""
    text, source_type = await extract_text(file_bytes, filename)
    
    doc = RAGDocument(
        title=title,
        source_type=source_type,
        content_raw=text,
        metadata_info={"filename": filename}
    )
    db.add(doc)
    await db.flush() # Pour avoir l'ID
    
    # Ajout des règles d'accès
    for role in allowed_roles:
        access = RAGDocumentAccess(document_id=doc.id, allowed_role=role.value)
        db.add(access)
        
    # Chunking et embeddings
    chunks = chunk_text(text)
    for i, chunk in enumerate(chunks):
        embedding = await get_embedding(chunk)
        rag_chunk = RAGChunk(
            document_id=doc.id,
            chunk_index=i,
            content=chunk,
            embedding=embedding,
            token_count=len(tiktoken.get_encoding("cl100k_base").encode(chunk))
        )
        db.add(rag_chunk)
        
    await db.commit()
    await db.refresh(doc)
    return doc


async def retrieve_context(db: AsyncSession, query: str, user_role: str, top_k: int = 3) -> list[dict]:
    """Recherche de similarité vectorielle avec filtrage par rôle (RBAC)."""
    query_embedding = await get_embedding(query)
    
    # Récupérer tous les chunks accessibles par le rôle
    # En prod avec pgvector : query_embedding <=> embedding
    stmt = (
        select(RAGChunk, RAGDocument)
        .join(RAGDocument, RAGChunk.document_id == RAGDocument.id)
        .join(RAGDocumentAccess, RAGDocument.id == RAGDocumentAccess.document_id)
        .where(RAGDocumentAccess.allowed_role == user_role)
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    # Calcul manuel de la similarité cosinus (fallback pour SQLite/Postgres sans pgvector)
    scored_chunks = []
    for chunk, doc in rows:
        if chunk.embedding:
            score = cosine_similarity(query_embedding, chunk.embedding)
            scored_chunks.append({
                "score": score,
                "content": chunk.content,
                "title": doc.title
            })
            
    # Trier par score décroissant et prendre les top_k
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]


from app.services.security_guardrails import check_input_guardrails, check_output_guardrails, trigger_ai_security_alert
from app.models.enums import AlertSeverityEnum

async def ask_rag(db: AsyncSession, question: str, user_role: str, user_id: uuid.UUID, interaction_id: uuid.UUID) -> dict:
    """Processus complet de RAG : Sécurité -> Retriever -> LLM -> Sécurité Sortie -> Réponse."""
    
    # 1. Guardrail d'entrée (Input Validation & Prompt Injection)
    is_safe_input, event_type, reason = check_input_guardrails(question)
    if not is_safe_input:
        await trigger_ai_security_alert(db, interaction_id, event_type, AlertSeverityEnum.CRITIQUE, reason)
        return {
            "status": "denied",
            "answer": "Votre requête a été bloquée pour des raisons de sécurité (politique interne). Un administrateur a été notifié.",
            "sources": []
        }
        
    # 2. Retriever (Recherche Vectorielle filtrée par Rôle)
    context_items = await retrieve_context(db, question, user_role, top_k=3)
    
    if not context_items or context_items[0]["score"] < 0.2: # Seuil minimal
        return {
            "status": "success",
            "answer": "Je n'ai pas trouvé d'information validée dans notre base de connaissances RH pour répondre à cette question.",
            "sources": []
        }
        
    # 3. LLM Generation
    is_placeholder = (
        not settings.OPENAI_API_KEY
        or settings.OPENAI_API_KEY.startswith("sk-proj-xxx")
        or "change" in settings.OPENAI_API_KEY.lower()
    )

    if is_placeholder and settings.DEBUG:
        source_titles = ", ".join(list(set([item["title"] for item in context_items])))
        answer = f"[Mode Démo/Mock] En réponse à votre question '{question}', voici les informations trouvées dans nos documents de référence ({source_titles}) :\n\n"
        for item in context_items:
            # Nettoyer un peu l'affichage pour le rendre professionnel
            content_cleaned = "\n  ".join([line.strip() for line in item["content"].strip().split("\n") if line.strip()])
            answer += f"📖 **{item['title']}** :\n  {content_cleaned}\n\n"
        answer += "*(Note: Cette réponse a été générée localement en mode Démo sans faire d'appel à l'API OpenAI)*"
        
        sources = list(set([item["title"] for item in context_items]))
        return {
            "status": "success",
            "answer": answer,
            "sources": sources
        }

    context_text = "\n\n".join([f"[Source: {item['title']}]\n{item['content']}" for item in context_items])
    
    system_prompt = """Tu es l'assistant IA RH officiel de l'entreprise.
Réponds à la question de l'employé de manière professionnelle, concise et empathique.
Utilise UNIQUEMENT le contexte fourni ci-dessous. Si la réponse n'y est pas, dis-le clairement.
Ne donne jamais de conseils médicaux ou juridiques non présents dans le texte."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Contexte:\n{context_text}\n\nQuestion: {question}"}
    ]
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0
        )
        answer = response.choices[0].message.content
        sources = list(set([item["title"] for item in context_items]))
        
        # 4. Guardrail de sortie (Data Leakage)
        is_safe_output, out_event_type, out_reason = check_output_guardrails(answer)
        if not is_safe_output:
            await trigger_ai_security_alert(db, interaction_id, out_event_type, AlertSeverityEnum.FUITE_DONNEES, out_reason)
            return {
                "status": "denied",
                "answer": "La réponse a été bloquée car elle contient des données potentiellement sensibles (Data Leak Prevention).",
                "sources": sources
            }
            
        return {
            "status": "success",
            "answer": answer,
            "sources": sources
        }
    except Exception as e:
        logger.error(f"Erreur génération LLM: {e}")
        return {
            "status": "error",
            "answer": "Une erreur technique est survenue lors de la génération de la réponse.",
            "sources": []
        }
