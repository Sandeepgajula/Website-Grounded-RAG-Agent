# Python Documentation Evaluation Benchmark

This document outlines the standard 15-question evaluation suite used to verify the performance, accuracy, and anti-hallucination guardrails of the Website RAG Agent when grounded on Python Documentation.

Target Ground Truth Website: **Python 3 Documentation** (`https://docs.python.org/3/`)

---

## 1. Factual / Retrieval Queries (Q1–Q5)
*These test the agent's ability to retrieve specific definitions, methods, or syntax rules directly stated on a single page.*

### Q1: What is a Python generator and how do you create one?
- **Category**: Factual
- **Expected Answer**: A generator is a function that returns an iterator. It is created using the `yield` keyword instead of `return`.
- **Expected Citations**: `https://docs.python.org/3/glossary.html`, `https://docs.python.org/3/tutorial/classes.html`
- **Pass Criteria**: Mentions `yield`, `iterator`, and `generator`.

### Q2: What is the difference between a list and a tuple in Python?
- **Category**: Factual
- **Expected Answer**: Lists are mutable sequences, typically used to store collections of homogeneous items, while tuples are immutable sequences, typically used to store collections of heterogeneous data.
- **Expected Citations**: `https://docs.python.org/3/tutorial/datastructures.html`
- **Pass Criteria**: Explicitly states lists are mutable and tuples are immutable.

### Q3: How does Python's Global Interpreter Lock (GIL) work?
- **Category**: Factual
- **Expected Answer**: The GIL is a mutex that protects access to Python objects, preventing multiple native threads from executing Python bytecodes at once in CPython.
- **Expected Citations**: `https://docs.python.org/3/glossary.html`
- **Pass Criteria**: Mentions CPython, mutex/lock, and threads.

### Q4: What are Python decorators and how are they used?
- **Category**: Factual
- **Expected Answer**: A decorator is a function returning another function, usually applied as a function transformation using the `@wrapper` syntax.
- **Expected Citations**: `https://docs.python.org/3/glossary.html`
- **Pass Criteria**: Mentions the `@` syntax or function wrapping.

### Q5: What is the purpose of Python's __init__ method?
- **Category**: Factual
- **Expected Answer**: `__init__` is a constructor-like method called when a new instance of a class is created to initialize the object's state.
- **Expected Citations**: `https://docs.python.org/3/tutorial/classes.html`
- **Pass Criteria**: Identifies it as used for initialization or constructor logic of an instance.

---

## 2. Synthesis & Conceptual Queries (Q6–Q10)
*These test the agent's ability to connect concepts across multiple sections or explain mechanisms.*

### Q6: How do context managers and the 'with' statement work in Python?
- **Category**: Synthesis
- **Expected Answer**: The `with` statement simplifies exception handling by encapsulating common preparation and cleanup tasks. It requires a context manager that implements `__enter__()` and `__exit__()` methods.
- **Expected Citations**: `https://docs.python.org/3/reference/datamodel.html`
- **Pass Criteria**: Mentions the `with` statement and `__enter__`/`__exit__`.

### Q7: Explain Python's exception handling mechanism.
- **Category**: Synthesis
- **Expected Answer**: Python uses `try`, `except`, `else`, and `finally` blocks. Code that might raise an exception goes in `try`, error handling in `except`, and cleanup in `finally`. Exceptions can be manually triggered using `raise`.
- **Expected Citations**: `https://docs.python.org/3/tutorial/errors.html`
- **Pass Criteria**: Mentions `try`, `except`, and `raise`.

### Q8: What are Python's built-in data structures?
- **Category**: Synthesis
- **Expected Answer**: Python provides several built-in data structures including lists, dictionaries (dicts), sets, and tuples.
- **Expected Citations**: `https://docs.python.org/3/tutorial/datastructures.html`
- **Pass Criteria**: Mentions `list`, `dict`, `set`, and `tuple`.

### Q9: How does async/await work in Python?
- **Category**: Synthesis
- **Expected Answer**: `async` and `await` are syntax for writing concurrent code using coroutines, heavily utilized by the `asyncio` library to run IO-bound tasks concurrently without threads.
- **Expected Citations**: `https://docs.python.org/3/library/asyncio.html`
- **Pass Criteria**: Mentions coroutines and `asyncio`.

### Q10: What is list comprehension and how does it differ from a for loop?
- **Category**: Synthesis
- **Expected Answer**: List comprehensions provide a concise way to create lists. They are generally more compact and faster than using standard `for` loops with `.append()`.
- **Expected Citations**: `https://docs.python.org/3/tutorial/datastructures.html`
- **Pass Criteria**: Mentions creating lists concisely vs standard `for` loop.

---

## 3. Negative / Out-of-Scope Queries (Q11–Q15)
*These test the anti-hallucination guardrails. The agent MUST refuse to answer these questions.*

### Q11: What is the monthly subscription price of Python Pro Enterprise edition?
- **Category**: Negative
- **Expected Answer**: Refuses to answer. There is no such thing as "Python Pro Enterprise edition" subscription in the documentation.
- **Pass Criteria**: States it does not have information.

### Q12: How do I install Python on a Raspberry Pi 5 using Docker Compose?
- **Category**: Negative
- **Expected Answer**: Refuses to answer based solely on the documentation (unless specific Docker compose instructions are literally in the Python 3 docs, which they are not).
- **Pass Criteria**: States it does not have information in the provided context.

### Q13: What is the total revenue of the Python Software Foundation in 2024?
- **Category**: Negative
- **Expected Answer**: Refuses to answer. Revenue data is not part of the standard Python language documentation.
- **Pass Criteria**: States it does not have information.

### Q14: Who won the 2024 UEFA European Football Championship final?
- **Category**: Negative
- **Expected Answer**: Refuses to answer. Unrelated to Python.
- **Pass Criteria**: States it does not have information.

### Q15: Does Python have a built-in iOS app for personal budgeting?
- **Category**: Negative
- **Expected Answer**: Refuses to answer. Python is a programming language, not an iOS app.
- **Pass Criteria**: States it does not have information.
