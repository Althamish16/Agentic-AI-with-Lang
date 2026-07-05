# Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation, or RAG, is a technique that grounds a large
language model's answers in an external knowledge source instead of relying only
on the model's parametric memory. A RAG pipeline has two phases: an *indexing*
phase that loads documents, splits them into chunks, embeds those chunks into
vectors, and stores them in a vector database; and a *query* phase that embeds the
user's question, retrieves the most similar chunks, and passes them to the model
as context.

The main benefit of RAG is that answers can cite specific, up-to-date sources,
which reduces hallucination. Because the knowledge lives outside the model, you
can update it by re-indexing documents rather than retraining the model. This makes
RAG especially useful for private company data, fast-changing information, and
question-answering over large document collections.

Good RAG systems pay careful attention to chunking. Chunks that are too large
dilute the relevant signal and waste context window; chunks that are too small
lose the surrounding meaning. A common starting point is 500 to 1000 characters
per chunk with a 10 to 20 percent overlap so that ideas spanning a boundary are
not lost.

Retrieval quality also depends on the search strategy. Plain similarity search
returns the closest vectors, but it can return several near-duplicate chunks.
Maximal Marginal Relevance (MMR) re-ranks results to balance relevance against
diversity, which often produces a more useful set of citations.

A production RAG answer should always include citations back to the source
documents so a human can verify the claim. This is the foundation the Research
Assistant in this course builds on.
