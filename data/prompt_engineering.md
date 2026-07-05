# Prompt Engineering and Structured Output

Prompt engineering is the practice of designing the text and structure of the
input given to a language model so that it produces reliable, useful output. Small
changes in wording, ordering, and formatting can meaningfully change results.

Prompt templates separate the fixed instructions from the variable inputs. Instead
of concatenating strings by hand, a template defines placeholders such as
{question} or {context} that are filled at runtime. This keeps prompts consistent,
testable, and reusable across an application.

A recurring need in agentic systems is *structured output* — getting the model to
return data in a strict shape, such as JSON, rather than free-form prose. Two common
approaches are: parsing the model's text with an output parser that validates it
against a schema (for example a Pydantic model), and using the provider's native
tool-calling or JSON mode to force valid structure. Structured output is what lets
one step's result feed cleanly into the next step of a pipeline.

Several patterns improve reliability. Few-shot prompting includes a handful of
worked examples. Chain-of-thought prompting asks the model to reason step by step
before answering. Giving the model an explicit role ("You are a meticulous research
assistant") sets tone and behavior. Clear formatting instructions, and an example
of the exact output shape, reduce parsing errors.

Finally, self-critique or reflection prompting asks the model to review and improve
its own draft against a checklist. A reflection step can catch missing citations,
unsupported claims, or unclear writing before the answer is shown to a user, which
is the basis of self-improving agents.
