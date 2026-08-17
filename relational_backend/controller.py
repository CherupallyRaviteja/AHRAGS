from rag_index import RAGIndex
from generator import generate_answer
from config import SIM_THRESHOLD
from query_rewriter import rewrite_query

rag = RAGIndex()
def main(question):
    
    q = question
    q = rewrite_query(q)
    results = rag.retrieve(q)
    score = f"Retrieved {len(results)} results. Top score: {results[0][3] if results else 'N/A'}"
    if not results or results[0][3] < SIM_THRESHOLD:
        return "I don't know.", {}, "No relevant sources found"

    contexts = []
    sources = []

    for content, source, page, score, *_ in results:
        contexts.append(content)
        sources.append((source, page))

    answer = generate_answer(q, contexts)
    print("Bot:", answer)
    print("\nSources:")
    sources = {source: page for source, page in set(sources)}  # Remove duplicates
    return answer, sources, score
