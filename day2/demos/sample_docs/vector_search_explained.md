# Vector Search, Explained From the Ground Up

## From text to numbers: embeddings

An embedding model reads a piece of text and outputs a vector — a fixed-length
list of numbers, typically a few hundred to a few thousand of them. The vector
is a coordinate in a high-dimensional space, and the model is trained so that
*text with similar meaning lands at nearby coordinates*. "The cat sat on the
mat" and "A feline rested on the rug" share almost no words, yet their vectors
point in nearly the same direction. That single property — closeness in space
equals similarity in meaning — is the foundation that all of semantic search,
RAG, and vector databases are built on.

The dimensionality of the vector is fixed by the model. BAAI's bge-small-en
produces 384 numbers per text; OpenAI's text-embedding-3-small produces 1,536;
text-embedding-3-large produces 3,072. Every vector in a collection must come
from the same model, because coordinates from different models are not
comparable — dimension 42 of one model has nothing to do with dimension 42 of
another. Mixing models in one index, or indexing with one model and querying
with another, silently breaks search.

## Measuring closeness: cosine similarity

Once texts are vectors, "how similar are these two texts?" becomes "how close
are these two vectors?". The most common measure is cosine similarity: the
cosine of the angle between the two vectors. It ranges from 1.0 (same
direction, essentially the same meaning) through 0.0 (unrelated) to -1.0
(opposite). Because cosine ignores vector length and looks only at direction,
vectors are often normalized to unit length first, after which cosine
similarity is just a dot product — one multiply-add per dimension, which is
why it is so fast.

Euclidean distance is the other common measure: the straight-line distance
between the two points. On normalized vectors, cosine similarity and Euclidean
distance rank neighbors identically, so the choice matters less than people
assume. What matters far more is that the embedding model is good and that
the same model embeds both sides of the comparison.

## What a vector database actually does

A vector database stores embeddings together with the original text and its
metadata, and answers one query extremely well: "given this query vector,
return the k stored vectors closest to it". A naive implementation compares
the query against every stored vector — fine for thousands of chunks, hopeless
for millions. Real vector databases build an *approximate nearest neighbor*
(ANN) index, most commonly HNSW (Hierarchical Navigable Small World graphs),
which organizes vectors into a layered graph that can be navigated to the
neighborhood of the query in logarithmic time. The result is approximate — it
might occasionally miss the true nearest neighbor — but in practice recall is
high and queries return in milliseconds.

Chroma is a lightweight open-source vector database that runs inside your
Python process with no separate server, persists to a local folder, and speaks
LangChain natively. That makes it ideal for prototypes, teaching labs, and
small production workloads. FAISS is a similar in-process library from Meta.
Pinecone, Weaviate, Qdrant, and Milvus are client-server databases built for
scale, and pgvector bolts vector search onto PostgreSQL so your embeddings
can live next to your relational data.

## Choosing an embedding model

Choosing an embedding model is a trade-off between quality, speed, cost, and
privacy. Large hosted models such as text-embedding-3-large capture more
nuance and top the retrieval benchmarks, but every embedding call is a network
round-trip that costs money and ships your text to an API. Small local models
such as bge-small-en run on CPU in milliseconds, cost nothing per call, work
offline, and keep data on your machine — at some cost in retrieval quality
that, for many applications, is barely measurable.

A rule of thumb for the classroom and for prototypes: start with a small local
model, get the pipeline working end to end, and only upgrade the embedding
model if retrieval quality — measured on real questions — is the bottleneck.
Remember that switching embedding models means re-indexing everything: the old
vectors and the new ones live in different coordinate systems, and the vector
dimensions usually do not even match.

## Why near-duplicates cluster together

Because closeness in embedding space means similarity in meaning, two chunks
that say the same thing in different words sit almost on top of each other in
the vector space. This is exactly what you want for search — but it creates
the redundancy problem in retrieval: the top-k nearest neighbors of a query
are often several restatements of the same passage. When a corpus repeats
itself, plain similarity search returns the repetition. Diversity-aware
strategies such as Maximal Marginal Relevance exist precisely to spend the
top-k budget on k *different* pieces of information rather than one piece of
information k times.

## A worked mental model

Picture every chunk in your corpus as a star in a night sky, where stars that
mean similar things form constellations. Indexing is charting the stars.
A query is a new point of light: retrieval finds the constellation it belongs
to and returns its nearest stars. Chunking decides how big each star is —
merge too much text into one star and it sits vaguely between constellations;
split too finely and single stars carry no meaning. And the embedding model is
the telescope: swap telescopes between charting and searching, and the map no
longer matches the sky at all.
