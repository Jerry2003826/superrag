# Architecture

The engine is organized around traceable evidence objects.

1. Register literature metadata and source documents.
2. Parse documents into chunks and evidence spans with physical provenance.
3. Extract result nodes from a single paper at a time.
4. Build retrieval indexes over verified evidence.
5. Synthesize only from evidence packs and block unsupported claims.
