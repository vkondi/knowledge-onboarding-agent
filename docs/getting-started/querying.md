# Querying the Knowledge Base

Make sure the virtual environment is active and Ollama is running before using any of these commands.

## Ask a question

```bash
koa ask "What are decorators in Python and how do you use them?"
```

The answer is synthesised by the local Ollama LLM using only the retrieved document chunks as context. Source files are listed below the answer:

```
Decorators in Python are functions that wrap another function to extend its
behavior without modifying it directly. They allow for adding new functionality
to existing functions or methods, such as logging, caching, or error handling.

To create a decorator, you define a function that takes another function as an
argument and returns a new function. The returned function is the decorated
version of the original function. Here's an example:

    def timer(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            print(f"{func.__name__} took {elapsed:.4f}s")
            return result
        return wrapper

To use a decorator, apply it to the function you want to decorate:

    @timer
    def slow_function():
        time.sleep(0.5)

Sources:
  • sample-knowledge\python-advanced.md
  • sample-knowledge\python-basics.md
```

If the knowledge base does not contain relevant content, the LLM responds with exactly: `"I don't have enough information to answer that."`

## Detect conflicting information

```bash
koa conflicts "git workflow"
```

Retrieves chunks related to the topic and asks the LLM to identify factual contradictions between them. Useful when the same topic appears in multiple documents with differing details:

```
There are no contradictions found in the provided text passages. However, there
is a slight difference in the command for creating and switching to a new branch:

In git-guide.md, two approaches are shown:
  git branch feature/login
  git checkout feature/login
or the combined:
  git checkout -b feature/login

In git-workflows.md, only the combined form is shown:
  git checkout -b feature/user-profile

Both methods achieve the same result. No factual contradiction exists.
```

When a genuine contradiction is found, the LLM describes it clearly: `"Source A says X, but Source B says Y."`

## Generate a learning path

```bash
koa path "machine learning"
```

Returns indexed documents on the topic ordered for progressive reading - grouped by source file, preserving the author's original chunk order:

```
Suggested reading order for 'machine learning':

sample-knowledge\deep-learning.md
  [0] Deep learning is a subfield of machine learning that uses neural networks with…
  [10] - Dropout: randomly zeroes neuron activations during training - prevents co-…
  [12] Train on a large dataset (e.g., ImageNet, a large text corpus), then fine-tune…

sample-knowledge\machine-learning-intro.md
  [0] Machine learning (ML) is a branch of artificial intelligence that allows…
  [1] The model learns from labelled training data - each input has a corresponding…
  [6] - Overfitting: Model memorises training data but performs poorly on new data.…
  [7] | Library | Purpose | |---|---| | scikit-learn | Classical ML algorithms,…
```

## CLI reference

| Command | Description |
|---|---|
| `koa ingest <path> [path …]` | Index markdown files from one or more files or directories |
| `koa watch [path …]` | Watch paths and re-index on change - uses `settings.yaml` if no path given (Ctrl+C to stop) |
| `koa reingest [path …]` | Wipe the vector store and re-index from scratch |
| `koa ask "<question>"` | Answer a natural-language question using the knowledge base |
| `koa conflicts "<topic>"` | Detect contradictions between sources on a topic |
| `koa path "<topic>"` | Suggest a progressive reading order for a topic |

---

Next: [Development](development.md) | [Troubleshooting](troubleshooting.md)
