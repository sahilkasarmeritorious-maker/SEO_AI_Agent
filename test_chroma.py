import argparse
import json
import sys
from pathlib import Path

import chromadb

CHROMA_PERSIST_PATH = "./chroma_db"  # must match chroma_service.py
COLLECTION_NAME = "analyses"


def get_collection():
    path = Path(CHROMA_PERSIST_PATH)
    if not path.exists():
        print(f"\n❌  Path '{path.resolve()}' does not exist.")
        print("    → Either the API has never run, or CHROMA_PERSIST_PATH is wrong.")
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(path))
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        return collection
    except Exception:
        print(f"\n❌  Collection '{COLLECTION_NAME}' not found in {path.resolve()}")
        print("    → The API ran but no analysis was ever saved.")
        sys.exit(1)


def cmd_stats(collection):
    total = collection.count()
    print(f"\n{'='*55}")
    print(f"  ChromaDB path : {Path(CHROMA_PERSIST_PATH).resolve()}")
    print(f"  Collection    : {COLLECTION_NAME}")
    print(f"  Total chunks  : {total}")
    print(f"{'='*55}")

    if total == 0:
        print("\n⚠️   Collection is empty — no analyses have been saved yet.")
        return

    # Show breakdown by user
    all_docs = collection.get()
    user_counts: dict = {}
    analysis_ids: dict = {}

    for meta in all_docs["metadatas"]:
        uid = meta.get("user_id", "unknown")
        aid = meta.get("analysis_id", "unknown")
        user_counts[uid] = user_counts.get(uid, 0) + 1
        analysis_ids.setdefault(uid, set()).add(aid)

    print("\n  Breakdown by user:")
    for uid, count in user_counts.items():
        aids = sorted(analysis_ids[uid])
        print(f"    user_id={uid}  →  {count} chunks  |  analyses: {aids}")
    print()


def cmd_user(collection, user_id: int):
    print(f"\n🔍  Fetching all chunks for user_id={user_id} ...")
    results = collection.get(where={"user_id": {"$eq": user_id}})
    ids = results.get("ids", [])

    if not ids:
        print(f"\n❌  No data found for user_id={user_id}")
        print("    Possible reasons:")
        print("    • Wrong user_id (check your JWT or DB)")
        print("    • Analysis hasn't completed yet (status != 'completed')")
        print("    • Data was saved with a different type (try --user_id as string?)")
        return

    print(f"\n✅  Found {len(ids)} chunks for user_id={user_id}\n")

    # Group by analysis
    by_analysis: dict = {}
    for i, meta in enumerate(results["metadatas"]):
        aid = meta.get("analysis_id")
        by_analysis.setdefault(aid, []).append({
            "id": ids[i],
            "chunk_type": meta.get("chunk_type"),
            "url": meta.get("url"),
            "seo_score": meta.get("seo_score"),
            "ux_score": meta.get("ux_score"),
            "document_preview": results["documents"][i][:120].replace("\n", " "),
        })

    for aid, chunks in by_analysis.items():
        url = chunks[0]["url"]
        seo = chunks[0]["seo_score"]
        ux  = chunks[0]["ux_score"]
        print(f"  Analysis ID : {aid}")
        print(f"  URL         : {url}")
        print(f"  SEO Score   : {seo}   UX Score: {ux}")
        print(f"  Chunks ({len(chunks)}):")
        for c in chunks:
            print(f"    [{c['chunk_type']:25s}] {c['document_preview']}...")
        print()


def cmd_query(collection, user_id: int, question: str):
    """Simple keyword search (no embeddings needed for this test)."""
    print(f"\n🔍  Searching for '{question}' (user_id={user_id}) ...")

    # Get all docs for this user and do a basic substring match
    results = collection.get(where={"user_id": {"$eq": user_id}})
    ids = results.get("ids", [])

    if not ids:
        print(f"\n❌  No data for user_id={user_id} — run stats check first.")
        return

    matches = [
        (ids[i], results["metadatas"][i], results["documents"][i])
        for i in range(len(ids))
        if question.lower() in results["documents"][i].lower()
    ]

    if not matches:
        print(f"\n⚠️   No chunks contained '{question}' — try a broader keyword.")
        print(f"     (Total chunks for this user: {len(ids)})")
        return

    print(f"\n✅  {len(matches)} matching chunks:\n")
    for doc_id, meta, doc in matches:
        print(f"  Chunk     : {doc_id}")
        print(f"  Type      : {meta.get('chunk_type')}")
        print(f"  URL       : {meta.get('url')}")
        print(f"  Content   :\n{doc}\n")
        print("-" * 50)


def main():
    parser = argparse.ArgumentParser(description="ChromaDB persistence test")
    parser.add_argument("--user_id", type=int, default=None,
                        help="User ID to inspect (required for --user and --query)")
    parser.add_argument("--query",   type=str, default=None,
                        help="Keyword to search inside stored documents")
    args = parser.parse_args()

    collection = get_collection()

    # Always show global stats
    cmd_stats(collection)

    if args.user_id is not None:
        cmd_user(collection, args.user_id)

        if args.query:
            cmd_query(collection, args.user_id, args.query)
    else:
        print("💡  Tip: add --user_id 1 to inspect a specific user's data.")
        print("         add --query 'SEO' to search inside documents.\n")


if __name__ == "__main__":
    main()