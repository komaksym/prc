Answer the frozen questions below using only the files in this folder.
Return one JSON object with an `answers` list. Each entry has its question `id`
and an `answer`. Use only the requested answer form. Do not explain answers.
For exact names, code and booleans, return only the exact value. For sets, return
a JSON array of exact items, or an empty array when none apply. For locations,
return `path::symbol`. Return `CANNOT TELL` only when this packet cannot show
the answer. For free text, use one short sentence with the requested facts.

Questions:
q1 (free): What behaviour changes for the owner of the connection reports, and for whom?
q2 (exact): Which class carries the main change?
q3 (exact_code): What exact provider message does the new code accept as normal snapshot completion?
q4 (set): Which other files or areas change besides the main source module?
q5 (set_or_none): Which risky surface does it touch (CI, dependencies, auth, schema, secrets, external calls), or none?
q6 (name_or_free): Which behaviour do the new tests pin?
q7 (location): Where should a reviewer start reading?
q8 (bool): True or false: this run activates reporting, collects live data, or changes schema.
