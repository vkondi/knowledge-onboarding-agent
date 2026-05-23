# Querying the Knowledge Base

Make sure the virtual environment is active and Ollama is running before using any of these commands.

## Ask a question

```bash
koa ask "What is the onboarding process for new employees?"
```

The answer is synthesised by the local Ollama LLM using only the retrieved document chunks as context. Source files are listed below the answer:

```
New employees should complete their orientation checklist on day one, including
setting up system access, meeting their team lead, and completing the mandatory
compliance training module.

Sources:
  • /notes/onboarding/new-hire-guide.md
  • /notes/hr/compliance.md
```

## Detect conflicting information

```bash
koa conflicts "probation period length"
```

Retrieves chunks related to the topic and asks the LLM to identify factual contradictions between them. Useful when the same policy appears in multiple documents with differing details.

## Generate a learning path

```bash
koa path "Kubernetes networking"
```

Returns indexed documents on the topic ordered for progressive reading — grouped by source file, preserving the author's original chunk order:

```
Suggested reading order for 'Kubernetes networking':

/notes/k8s/01-basics.md
  [0] Kubernetes networking uses a flat network model where every Pod …
  [1] Services abstract Pod IP addresses behind a stable virtual IP …

/notes/k8s/02-ingress.md
  [0] An Ingress resource defines HTTP routing rules for external traffic …
```

## CLI reference

| Command | Description |
|---|---|
| `koa ingest <path> [path …]` | Index markdown files from one or more files or directories |
| `koa watch [path …]` | Watch paths and re-index on change — uses `settings.yaml` if no path given (Ctrl+C to stop) |
| `koa reingest [path …]` | Wipe the vector store and re-index from scratch |
| `koa ask "<question>"` | Answer a natural-language question using the knowledge base |
| `koa conflicts "<topic>"` | Detect contradictions between sources on a topic |
| `koa path "<topic>"` | Suggest a progressive reading order for a topic |

---

Next: [Development](development.md) | [Troubleshooting](troubleshooting.md)
