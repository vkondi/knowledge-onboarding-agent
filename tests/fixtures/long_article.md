# Vector Databases and Semantic Search

Vector databases are purpose-built storage systems for high-dimensional embedding
vectors. Unlike traditional relational databases that match records on exact
field values, vector databases find records by geometric proximity in a
high-dimensional space. This makes them the natural backend for semantic search,
recommendation systems, and retrieval-augmented generation pipelines.

## What Makes a Vector Database Different

A relational database answers the question: "give me all rows where field equals
value." A vector database answers a fundamentally different question: "give me the
rows whose vectors are closest to this query vector." This is called
approximate nearest-neighbor (ANN) search.

ANN search is approximate because exact nearest-neighbor search in high
dimensions is prohibitively expensive. The curse of dimensionality means that
brute-force distance comparisons become impractical as the number of dimensions
grows. ANN algorithms like HNSW, IVF, and LSH trade a small amount of recall for
dramatic speedups — finding 95% of the true nearest neighbors in milliseconds
rather than seconds.

## Embedding Dimensions and Memory

Embedding dimension determines both the expressiveness of the representation and
the memory cost of storage. A 768-dimensional float32 vector occupies 3 KB.
One million such vectors require approximately 3 GB of RAM if held in memory.
This is a realistic corpus size for a personal knowledge base after several years
of note-taking, so memory budgeting is a genuine concern.

Smaller embedding dimensions (384) reduce memory but may sacrifice retrieval
quality. Larger dimensions (1536, 3072) improve quality at substantial memory
cost. For a local system constrained to 16 GB RAM, models in the 512–768
dimension range represent a practical sweet spot.

## Distance Metrics

The two most common similarity metrics in vector search are cosine similarity and
dot product. Cosine similarity measures the angle between two vectors, ignoring
magnitude. It is preferred when vectors have variable lengths and the direction
of the vector encodes the meaning. Dot product includes magnitude and can
amplify the influence of longer documents, which may or may not be desirable.

Most embedding models are trained to be used with cosine similarity. Unless the
model documentation specifies otherwise, cosine similarity is the safer default.
Euclidean distance (L2) is less common for embedding retrieval but is the default
metric in some FAISS index types.

## HNSW: The Dominant ANN Algorithm

Hierarchical Navigable Small World (HNSW) graphs are the dominant approach for
ANN search in production vector databases. HNSW constructs a multi-layer graph
where each node is a vector. During search, the algorithm enters the graph at
a coarse layer and greedily navigates toward the query vector, descending to
finer layers as it converges. This produces logarithmic search complexity.

HNSW has two key parameters: `M` (the number of connections per node) and
`ef_construction` (the quality of the graph during index construction). Higher
values produce better recall at the cost of more memory and slower indexing.
Default values of M=16 and ef_construction=200 are reasonable starting points
for most use cases.

## ChromaDB vs FAISS

ChromaDB is a dedicated vector database with built-in metadata storage, a Python
API, and persistence via SQLite. It handles the full document lifecycle:
insert, update, delete, and filtered query. It is easy to set up and requires no
configuration beyond a storage path. ChromaDB is the right default for a project
that needs to store and query documents with metadata filtering.

FAISS is a lower-level library from Meta that implements several ANN index
types with extremely high performance. FAISS has no built-in metadata storage —
it stores only integer IDs, and the caller must maintain a separate mapping from
IDs to documents. FAISS is the right choice when maximum throughput matters and
the application can manage its own metadata layer.

For a local personal knowledge base, ChromaDB's ease of use and built-in
persistence make it the better starting point. FAISS becomes relevant if the
corpus grows large enough that ChromaDB's performance becomes a bottleneck,
which is unlikely below one million documents.

## Incremental Indexing

A key design requirement for a continuously-running knowledge system is
incremental indexing: only re-embed documents that have actually changed. Full
re-indexing on every startup would be prohibitively slow for a large corpus.

The standard approach is content hashing. When a document is first ingested, its
SHA-256 hash is stored alongside the embedding. On subsequent ingestion, the
current hash is compared to the stored hash. If they match, the embedding is
current and can be skipped. Only changed or new documents proceed to the
(expensive) embedding step.

This requires the vector store to support an efficient lookup by document
identifier to retrieve the stored hash. ChromaDB supports this natively through
its metadata fields, making it well-suited for incremental indexing workflows.
