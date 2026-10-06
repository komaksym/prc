# Reader prompt (EVAL.md part C, all conditions)

Answer the 8 questions in `eval/questions/pr<N>.json` using ONLY the files in
this packet directory. Rules:

- Use only these files. Do not use any other knowledge, including knowledge
  of the repository, the PR, or the code.
- Quote code exactly: names, values, and snippets must be copied
  character-for-character from the packet files.
- Answer `CANNOT TELL` when the files do not show the answer. Never guess.
- For each question, give `id` and `answer` (a string, a list of strings for
  set questions, or `CANNOT TELL`).

Write your answers as JSON to the answers path for your PR and condition:

```json
{
  "pr": <N>,
  "condition": "<condition>",
  "answers": [
    {"id": "q1", "answer": "..."},
    {"id": "q2", "answer": "..."},
    {"id": "q3", "answer": "..."},
    {"id": "q4", "answer": ["..."]},
    {"id": "q5", "answer": "..."},
    {"id": "q6", "answer": "..."},
    {"id": "q7", "answer": "..."},
    {"id": "q8", "answer": "..."}
  ]
}
```

For q5, answer `none` (the string) when the packet shows no risky surface.
For q8, answer `true` or `false`.
