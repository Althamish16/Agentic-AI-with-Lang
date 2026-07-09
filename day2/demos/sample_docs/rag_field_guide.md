# A Field Guide to Retrieval-Augmented Generation

## What RAG is and why it exists

Retrieval-Augmented Generation (RAG) grounds a language model's answers in an
external knowledge source instead of relying only on what the model memorized
during training. The model's built-in knowledge is frozen at training time,
cannot cite where a fact came from, and knows nothing about your private
documents. RAG fixes all three problems at once: before answering, the system
retrieves the most relevant passages from your own document collection and
pastes them into the prompt, so the model answers from evidence it can cite.

A RAG system has two distinct phases that run at different times. The
*indexing* phase runs ahead of time: load documents, split them into chunks,
embed each chunk into a vector, and store the vectors in a vector database.
The *query* phase runs when a user asks a question: embed the question with
the same embedding model, retrieve the top-k most similar chunks, stuff those
chunks into the prompt as numbered context, and let the model generate an
answer with citations back to the chunks it used.

## The indexing phase: load, split, embed, store

Loading turns raw files into Document objects. A Document is just a container
holding the text (page_content) plus metadata such as the source file path and
the page number. The metadata matters more than beginners expect: it is what
makes citations possible later, because every retrieved chunk still remembers
exactly which file and position it came from.

Splitting is where most of the tuning happens. What chunk size should you
use? Chunks that are too large dilute the relevant signal — one vector ends up
"meaning" ten topics at once — and they waste precious context-window space on
irrelevant sentences. Chunks that are too small lose the surrounding meaning
that makes a passage interpretable: they retrieve well but answer badly. The
classic starting point for RAG is a chunk size of 500 to 1,000 characters with
a 10 to 20 percent overlap, and the honest way to tune from there is to read
what retrieval actually returns for real questions, not to trust intuition.

Overlap exists because ideas do not respect chunk boundaries. If an important
explanation straddles the cut point between chunk 7 and chunk 8, a query about
it might match neither half well. Repeating the last 100 or so characters of
each chunk at the start of the next one gives every idea at least one chunk
where it appears whole.

Embedding converts each chunk of text into a vector — a long list of numbers —
using an embedding model. The essential property is that text with similar
meaning produces vectors that are close together in space. "How do I reset my
password?" and "I forgot my login credentials" land near each other even
though they share almost no words. This is what lets retrieval work by meaning
rather than by keyword matching.

Storing puts the vectors into a vector database such as Chroma, along with the
chunk text and metadata. The database builds an index so that "find the k
nearest vectors to this query vector" is fast even with millions of chunks.

## The query phase: retrieve, augment, generate

At query time the user's question is embedded with the *same* embedding model
that indexed the chunks. This point is critical and a classic source of silent
failures: if the query is embedded with a different model than the documents,
the two sets of vectors live in unrelated coordinate systems, and nearest-
neighbor search returns essentially random chunks. Nothing errors — the
results are simply garbage.

The retriever returns the top-k chunks, typically 3 to 6. These are formatted
into a numbered context block and placed into the prompt together with the
question and an instruction like "answer using only the context below and cite
sources as [1], [2]". The model then generates the answer. Because the
evidence is in the prompt, the answer can quote it, cite it, and — just as
important — say "the context does not contain this" instead of hallucinating.

## Tuning chunking: the size and overlap knobs

Chunk size is the single most consequential knob in a RAG pipeline — so, what
chunk size should you use? Chunks that are too large dilute the relevant
signal — one vector ends up "meaning" ten topics at once — and they waste
precious context-window space on irrelevant sentences. Chunks that are too
small lose the surrounding meaning that makes a passage interpretable: they
retrieve well but answer badly. The classic starting point for RAG is a chunk
size of 500 to 1,000 characters with a 10 to 20 percent overlap, and the
honest way to tune from there is to read what retrieval actually returns for
real questions, not to trust intuition.

A practical tuning loop looks like this: pick ten questions your users
actually ask, run retrieval, and read the retrieved chunks with your own eyes.
If the chunks contain the answer but also pages of unrelated text, they are
too big. If the chunks are on-topic fragments that do not contain enough
context to answer, they are too small. If the answer keeps falling on a chunk
boundary, increase the overlap.

Splitter choice matters too. A naive splitter cuts every N characters, even
mid-word. RecursiveCharacterTextSplitter is the sensible default: it tries to
split on paragraph breaks first, then sentences, then words, and only cuts
mid-word as a last resort, so chunks tend to align with the document's natural
structure.

## Retrieval strategies: similarity search versus MMR

Plain similarity search returns the k chunks whose vectors are closest to the
query vector. It is simple and usually right, but it has a known failure mode:
redundancy. If your corpus says the same thing in three places — which real
corpora constantly do — similarity search happily returns all three near-
duplicate chunks, spending your whole context budget on one idea repeated
three times.

Maximal Marginal Relevance (MMR) trades a little relevance for diversity. It
first fetches a wider pool of candidates (fetch_k, often 20), then picks
results one at a time, each time choosing the chunk that is both similar to
the query *and* dissimilar to the chunks already picked. The lambda parameter
controls the balance: 1.0 is pure relevance, 0.0 is pure diversity, and 0.5 is
a common default. Use MMR when your documents overlap heavily in content or
when the question needs information from several distinct aspects of a topic.

## Common failure modes and how to spot them

Retrieval failures are usually silent: the pipeline runs, an answer appears,
and it is subtly wrong or vague. The three failures worth memorizing are:
chunks too large (answers become generic because the model is reading mostly
irrelevant text), chunks too small (answers lack grounding because no chunk
carries a complete thought), and embedding-model mismatch between indexing and
querying (retrieval returns unrelated chunks, and the model either refuses or
hallucinates). When a RAG system misbehaves, look at the retrieved chunks
before blaming the model — in most cases the generator was doomed by what
retrieval handed it.

A final habit that separates good RAG systems from bad ones: always show your
sources. Inline citations back to specific chunks let users verify claims, let
developers debug retrieval, and keep the model honest. If an answer cannot be
traced to a chunk, it should not be in the response.
