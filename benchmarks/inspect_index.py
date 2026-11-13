from pathlib import Path
from collections import Counter

import chromadb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "chroma_db"


def main():
    if not DB_PATH.is_dir():
        raise SystemExit(f"Database directory not found: {DB_PATH}")

    client = chromadb.PersistentClient(path=str(DB_PATH))

    collections = client.list_collections()
    if not collections:
        print("No collections found.")
        return

    for entry in collections:
        name = entry if isinstance(entry, str) else entry.name
        collection = client.get_collection(name=name)
        print(f"Collection: {name}")
        print(f"Stored records: {collection.count()}")

        records = collection.get(include=["documents", "metadatas"])

        source_counts = Counter()
        passage_counts = Counter()

        for text, metadata in zip(records["documents"], records["metadatas"]):
            source = (metadata or {}).get("source", "<unknown>")
            source_counts[source] += 1
            passage_counts[(source, text)] += 1

        # print("\nRecords per source:")
        # for source, count in source_counts.most_common():
        #     print(f"  {source}: {count}")

        unique_counts = Counter(source for source, text in passage_counts)

        print("\nRecords per source:")
        for source, total in source_counts.most_common():
            unique = unique_counts[source]
            extras = total - unique
            print(f"  {source}: stored={total}, unique={unique}, extras={extras}")


        duplicate_extras = sum(count - 1 for count in passage_counts.values() if count > 1)
        print(f"Extra exact-duplicate records: {duplicate_extras}")

        sample = collection.get(limit=2, include=["documents", "metadatas"])

        for record_id, text, metadata in zip(sample["ids"], sample["documents"], sample["metadatas"]):
            print(f"\nID: {record_id}")
            print(f"Metadata: {metadata}")
            print(f"Text preview: {(text or '')[:300]}")
        


if __name__ == "__main__":
    main()