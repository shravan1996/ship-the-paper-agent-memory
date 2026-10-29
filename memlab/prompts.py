"""Every prompt the prototype sends. The two arms share the answer and judge prompts word for word.

The extraction and update prompts follow the shape of Mem0's two phases (Chhikara et al., 2025):
pull candidate facts out of each new exchange, then compare them with the most similar stored
memories and choose ADD, UPDATE, DELETE or NONE for each. They are written for this prototype, not
copied from the Mem0 repository.
"""

EXTRACT = """You maintain the long-term memory of an AI assistant. Read one exchange between the user and the assistant and write down the facts worth remembering for future conversations with this user.

Keep:
- facts about the user: who they are, their situation, goals, projects, plans, deadlines, dates, numbers, decisions, and what they report having done;
- preferences and standing instructions about how the assistant should respond to them;
- changes to anything the user said before, stated with the new value;
- facts from the assistant's reply only when the user adopts, confirms or relies on them.

Drop greetings, generic advice, and code or explanations the user has not made their own.

Write each fact as one short, self-contained sentence about the user ("The user ..."), keeping names, numbers and dates exactly as written. If nothing is worth remembering, return an empty list.

The previous exchange is context only. Extract facts from the current exchange.

Return only JSON: {{"facts": ["...", "..."]}}

Date of the current exchange: {date}

Previous exchange (context only):
{previous}

Current exchange:
{current}"""

UPDATE = """You maintain the long-term memory of an AI assistant. New facts have just been extracted from a conversation with the user. Below them are the stored memories most similar to those facts. For each new fact, decide how memory should change:

- ADD: the fact is new information. Store it as a new memory.
- UPDATE: the fact adds to or changes a stored memory. Give that memory's id and the rewritten memory, keeping whatever is still true and stating the new value.
- DELETE: the fact shows a stored memory is no longer true and there is nothing to store in its place. Give that memory's id.
- NONE: the fact is already stored. Give the id of the memory that holds it.

Return only JSON: {{"operations": [{{"fact": 1, "event": "ADD", "text": "..."}}, {{"fact": 2, "event": "UPDATE", "id": 7, "text": "..."}}, {{"fact": 3, "event": "DELETE", "id": 4}}, {{"fact": 4, "event": "NONE", "id": 2}}]}}

Date of these facts: {date}

New facts:
{facts}

Stored memories:
{memories}"""

ANSWER = """You are the assistant in a long-running conversation with this user. {source} Use them to reply to the user's new message. If they do not contain what you need, say so plainly instead of guessing.

{context}

User's new message: {question}"""

SOURCE_RAW = "Below are passages retrieved from your earlier conversations with the user, each with its date."
SOURCE_MEMORY = "Below are notes from your long-term memory about this user, each with the date it was recorded."

JUDGE = """You are grading an AI assistant's reply against a rubric. For each rubric item, score 1 if the reply fully satisfies it, 0.5 if it partly does, and 0 if it does not. Judge only against the rubric. Do not reward length or confidence.

User's message:
{question}

Assistant's reply:
{answer}

Rubric:
{rubric}

Return only JSON with one score per rubric item, in order: {{"scores": [1, 0.5, 0]}}"""
