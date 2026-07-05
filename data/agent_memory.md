# Agent Memory: Short-Term and Long-Term

Memory is what turns a one-shot question-answerer into an assistant that can hold a
conversation and improve over time. It is useful to separate two kinds of memory.

Short-term memory is the working context of the current session or conversation. In
LangGraph this is typically the list of messages in the state, persisted by a
checkpointer under a thread identifier. When the user sends a follow-up like "and
what about the second one?", short-term memory is what lets the agent resolve
"the second one" from earlier turns. Short-term memory is scoped to a thread and is
usually discarded or archived when the conversation ends.

Long-term memory persists across sessions and threads. It stores durable facts,
user preferences, and useful findings so the agent can recall them weeks later. A
common implementation is a dedicated vector store: the agent writes a short note as
an embedded document, and later retrieves relevant notes by semantic search. This
is the same retrieval machinery used for RAG, applied to the agent's own memories
rather than to source documents.

A practical challenge is that short-term memory grows without bound. Long
conversations eventually exceed the model's context window and become expensive.
The standard remedy is *compaction* (also called summarization memory): older
messages are replaced with a concise summary that preserves the important facts and
decisions, while recent messages are kept verbatim. Compaction keeps cost and
latency stable while retaining continuity.

A well-designed agent uses both: short-term memory for the flow of the current
conversation, long-term memory for knowledge worth keeping, and compaction to stop
the context from exploding.
