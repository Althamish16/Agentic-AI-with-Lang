# Vector Databases and Embeddings

A vector database stores high-dimensional vectors (embeddings) and makes it fast
to find the vectors most similar to a query vector. Embeddings are numerical
representations of text, images, or other data produced by an embedding model.
Text with similar meaning maps to vectors that are close together, so semantic
search becomes a nearest-neighbor lookup.

Chroma is a lightweight, open-source vector database that can run entirely on your
local machine with no separate server process. It persists collections to disk,
which makes it a great choice for prototypes, labs, and small applications. Other
popular options include FAISS, Pinecone, Weaviate, Qdrant, and pgvector for
PostgreSQL.

Similarity between two vectors is usually measured with cosine similarity, which
compares the angle between them, or with Euclidean distance. Before comparing,
vectors are often normalized to unit length so that only direction matters.

Choosing an embedding model is a trade-off. Larger models such as OpenAI's
text-embedding-3-large capture more nuance but cost more and add network latency.
Small local models such as BAAI's bge-small-en run on CPU in milliseconds with no
API calls, which is ideal for offline development. The dimensionality of the
vector — for example 384, 768, or 1536 — is fixed by the model you choose, and all
vectors in a collection must share the same dimension.

A key operational detail is that the same embedding model must be used for both
indexing and querying. If you index with one model and query with another, the
vectors live in different spaces and retrieval quality collapses.
