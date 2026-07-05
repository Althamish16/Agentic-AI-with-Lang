# LangGraph and Agent Architectures

LangGraph is a library for building stateful, multi-step applications with large
language models. Where a plain LangChain chain runs a fixed sequence of steps,
LangGraph models the application as a graph: nodes are units of work (often an LLM
call or a tool call) and edges describe how control moves between them. A shared
State object flows through the graph, and each node returns updates to that state.

The power of the graph model is *conditional edges*. After a node runs, a routing
function inspects the state and decides which node to visit next. This is what lets
an agent loop — for example, calling a tool, observing the result, and deciding
whether to call another tool or produce a final answer. A plain chain cannot loop
or branch like this.

A common agent architecture is Planner → Executor → Memory. The planner decomposes
a goal into sub-tasks. The executor carries out each sub-task, often by calling
tools such as a retriever or a web search. Memory records what has been done so the
agent does not repeat work and can summarize its progress.

LangGraph adds durability through *checkpointers*. A checkpointer saves the graph
state after every step to a backend such as SQLite. Because state is persisted, a
run can be interrupted and later resumed from exactly where it stopped, and a
conversation can remember previous turns using a thread identifier.

More advanced systems use *multi-agent* designs. A supervisor agent delegates work
to specialized sub-agents — for instance a researcher that gathers facts and a
writer that composes the final report — and then aggregates their outputs. Each
sub-agent can itself be a graph, nested as a node inside the parent graph.
