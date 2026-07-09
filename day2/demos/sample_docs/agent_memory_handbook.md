# The Agent Memory Handbook

## Why memory is a separate problem

A language model has no memory of its own: every API call starts from a blank
slate, and the model only "remembers" whatever you place into the prompt of
that specific call. Everything we call agent memory is therefore engineering
on our side of the API — deciding what to store, where to store it, and what
to re-feed into the context window at the right moment. Memory is what turns
a one-shot question answerer into an assistant that can hold a conversation
this hour and recall your preferences next month.

## Short-term memory: the conversation thread

Short-term memory is the working context of the current session. In LangGraph
it is typically the list of messages in the graph state, saved by a
checkpointer under a thread identifier so that a conversation can pause and
resume. When the user sends a follow-up like "and what about the second one?",
short-term memory is what lets the agent resolve "the second one" from earlier
turns. It is scoped to a single thread and is usually discarded or archived
when the conversation ends.

Short-term memory has a built-in problem: it grows without bound. A long
conversation eventually exceeds the model's context window, and even before
that it gets slow and expensive, because every earlier message is re-sent and
re-processed on every new turn. The standard remedy is *compaction*, also
called summarization memory: older messages are replaced by a concise summary
that preserves the key facts and decisions, while the most recent messages are
kept verbatim. Compaction keeps cost and latency roughly constant while
retaining conversational continuity.

## Long-term memory: facts that survive the session

Long-term memory persists across sessions and threads. It holds durable facts
("the user's name is Priya"), preferences ("prefers morning appointments",
"answers should be concise"), and useful findings from past work, so the agent
can recall them days or weeks later in a completely new conversation.

The most common implementation is a dedicated vector store. When the agent
learns something worth keeping, it writes a short note and embeds it as a
document. Later, when a new conversation begins or a new question arrives, the
agent embeds the current context as a query and retrieves the most relevant
notes by semantic search. This is exactly the same retrieval machinery used
for RAG — load, embed, store, retrieve — applied to the agent's own memories
instead of to source documents. If you understand the RAG pipeline, you
already understand vector-store memory: only the content changes.

## Episodic memory: learning from past runs

Beyond facts and preferences, agents benefit from remembering *episodes*: what
task was attempted, what steps were taken, and how it turned out. An episode
log lets an agent answer "book the usual room" by finding the last few booking
episodes and reading what "usual" meant, or avoid repeating an approach that
failed last week. Episodic memories are typically stored as structured records
(task, steps, outcome, timestamp) and retrieved either by recency or by
semantic similarity to the current task.

## Retrieval is the heart of every memory system

Notice the pattern across all long-term designs: storage is cheap and easy,
and the hard part is *retrieval* — surfacing the right memory at the right
moment without flooding the context window. Store everything and retrieve
badly, and the agent drowns in irrelevant recollections; retrieve nothing, and
it is an amnesiac. Good memory systems therefore obsess over the same knobs as
good RAG systems: how items are chunked into notes, which embedding model
indexes them, how many results to retrieve, and how to keep near-duplicate
memories from crowding out diverse, useful ones.

A practical detail that trips up production systems: memories go stale. The
user changes teams, the preferred meeting room closes, the project gets
renamed. Mature memory systems attach timestamps, prefer recent memories when
two conflict, and periodically consolidate — merging near-duplicate notes and
deleting ones that later turned out to be wrong. Consolidation is to long-term
memory what compaction is to short-term memory: a hygiene process that keeps
the store small, current, and retrievable.

## Putting it together

A capable assistant runs several memories at once. The message thread gives it
short-term coherence; compaction keeps that thread affordable; a vector store
of notes gives it durable knowledge of the user; an episode log lets it reuse
what worked before. Each one is, underneath, the same loop you learn on Day 2:
write text, embed it, store the vector, retrieve by similarity, and feed what
you retrieved back into the prompt. An agent's memory is just RAG pointed at
its own experience.
