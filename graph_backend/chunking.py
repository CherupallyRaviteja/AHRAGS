from PyPDF2 import PdfReader
from sentence_transformers import util
from config import embed_model
import re

def watson_chunking(text, max_words=250):
    blocks, current = [], []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    for line in lines:
        if re.match(r"^[A-Z][A-Za-z\s]{3,}$", line) or re.match(r"^\d+[\.\)]", line):
            if current:
                blocks.append(" ".join(current))
                current = []
        current.append(line)
        if len(" ".join(current).split()) > max_words:
            blocks.append(" ".join(current))
            current = []

    if current:
        blocks.append(" ".join(current))

    chunks = [c for c in blocks if len(c.split()) > 5 or "\n" in c]
    return chunks


def pairwise_chunk_similarity(chunks, threshold=None):
    """
    Compute pairwise semantic similarity between chunks.

    Added per GraphRAG_Migration_Blueprint.md Section 4.8 ("Better Chunk
    Connections"). This reuses the exact same embedding + cosine-similarity
    primitive already used inside agentic_chunking() above (util.cos_sim on
    embed_model encodings), but applies it across whole chunks instead of
    consecutive sentences, and returns which pairs are similar enough to
    link rather than using the similarity to decide a split point.

    graph_builder.py uses this to create REFERENCES/EXTENDS edges between
    Chunk nodes. watson_chunking / agentic_chunking themselves are
    unmodified — this is purely an additive helper.

    Args:
        chunks: list of chunk text strings (as produced by watson_chunking).
        threshold: minimum cosine similarity to report a pair. Defaults to
            config.CHUNK_LINK_SIM_THRESHOLD if not given.

    Returns:
        List of (i, j, similarity) tuples for every pair i < j whose
        similarity is >= threshold.
    """
    if threshold is None:
        try:
            from config import CHUNK_LINK_SIM_THRESHOLD
            threshold = CHUNK_LINK_SIM_THRESHOLD
        except ImportError:
            threshold = 0.8

    if not chunks or len(chunks) < 2:
        return []

    embeddings = embed_model.encode(chunks, convert_to_tensor=True)
    linked_pairs = []

    for i in range(len(chunks)):
        for j in range(i + 1, len(chunks)):
            sim = util.cos_sim(embeddings[i], embeddings[j]).item()
            if sim >= threshold:
                linked_pairs.append((i, j, sim))

    return linked_pairs


if __name__ == "__main__":

    pdf_path = input("Enter the path to the PDF file: ")
    reader = PdfReader(pdf_path)
    text = ""

    for page in reader.pages:
        text += page.extract_text()

    chunks = watson_chunking(text)
        
    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i+1} ---")
        print(chunk)  
        print("\n")
