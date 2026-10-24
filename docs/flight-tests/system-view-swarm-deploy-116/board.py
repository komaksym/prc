"""Build board.json: system map before/after plus a walk of the changed error path.

Arena synthesis for swarm-deploy#116: candidate 1 base (one shared map) with candidate 3's
rule of drawing no arrow whose wiring is outside the diff. The walk tones one error type
per sentence behind a single loader-to-errors arrow, so no arrow crosses a box.

The marker § stands for a code-span backtick in captions.
"""

import json
from pathlib import Path

OUT = Path(__file__).parent

C = {
    "read": {
        "line": "internal/modules/gitops/git/repository.go:68",
        "match": "func (r *GoGitRepository) ReadFile",
    },
    "read_old": {
        "line": "internal/modules/gitops/git/repository.go:-70",
        "match": "return os.ReadFile(fullPath)",
    },
    "read_new": {
        "line": "internal/modules/gitops/git/repository.go:71",
        "match": "read repository file %q: %w",
    },
    "load": {"line": "internal/compose/file.go:75", "match": "func (l *fileLoader) Load"},
    "reader": {"line": "internal/compose/file.go:76", "match": "l.fileReader(ctx, path)"},
    "txt_read": {
        "line": "internal/compose/file.go:-77",
        "match": 'fmt.Errorf("read compose file %s: %w", path, err)',
    },
    "txt_decode": {"line": "internal/compose/file.go:-83", "match": "decode compose schema"},
    "link_old": {
        "line": "internal/compose/file.go:-152",
        "match": "linkServices(compose *Compose, baseDir string) error",
    },
    "jobs_old": {"line": "internal/compose/initjob.go:-21", "match": "([]InitJob, error)"},
    "jobs_first": {
        "line": "internal/compose/initjob.go:-24",
        "match": 'return nil, fmt.Errorf("init-jobs[%d]: image is required", i)',
    },
    "new_read": {
        "line": "internal/compose/file.go:78",
        "match": "&ReadComposeError{FilePath: path, Err: err}",
    },
    "new_parse": {
        "line": "internal/compose/file.go:83",
        "match": "&ParseComposeError{FilePath: path, Err: err}",
    },
    "new_decode": {
        "line": "internal/compose/file.go:88",
        "match": "&ValidateComposeError{FilePath: path, Issues: decodeIssues(err), Err: err}",
    },
    "new_link": {
        "line": "internal/compose/file.go:92",
        "match": "&ValidateComposeError{FilePath: path, Issues: issues}",
    },
    "link_new": {
        "line": "internal/compose/file.go:179",
        "match": "linkServices(compose *Compose, baseDir string) []ValidationIssue",
    },
    "link_name": {
        "line": "internal/compose/file.go:201",
        "match": "issue.ResourceName = service.Name",
    },
    "jobs_new": {
        "line": "internal/compose/initjob.go:21",
        "match": "([]InitJob, []ValidationIssue)",
    },
    "jobs_all": {"line": "internal/compose/initjob.go:30", "match": "continue"},
    "t_read": {"line": "internal/compose/errors.go:9", "match": "type ReadComposeError struct"},
    "t_parse": {"line": "internal/compose/errors.go:24", "match": "type ParseComposeError struct"},
    "t_issue": {"line": "internal/compose/errors.go:49", "match": "type ValidationIssue struct"},
    "t_val": {"line": "internal/compose/errors.go:63", "match": "type ValidateComposeError struct"},
    "f_err": {"line": "internal/shared/faults/faults.go:5", "match": "type Error interface"},
    "f_tmp": {"line": "internal/shared/faults/faults.go:9", "match": "Temporary() bool"},
    "caller": {
        "line": "internal/compose/errors_test.go:24",
        "match": 'loader.Load(context.Background(), "/stack/compose.yaml")',
    },
    "caller_path": {"line": "internal/compose/errors_test.go:34", "match": "readErr.FilePath"},
}


def cites(*keys):
    return [C[k] for k in keys]


def groups(after, slots=None):
    """Same five boxes and ids in every map scene; only subs, slots and cues change."""
    if slots is None:
        slots = not after
    slot = {"kind": "slot", "label": "added by this PR"} if slots else {}
    return [
        {
            "id": "g_git",
            "title": "gitops/git",
            "col": 0,
            "row": True,
            "sub": "repository.go: adds path to errors"
            if after
            else "repository.go: returns the bare OS error",
            "items": [{"id": "i_read", "text": "ReadFile"}],
        },
        {
            "id": "g_faults",
            "title": "shared/faults",
            "col": 0,
            "row": True,
            "sub": "faults.go: new, no caller yet" if after else "package does not exist",
            "items": [
                {"id": "f_err", "text": "Error", **slot},
                {"id": "f_tmp", "text": "Temporary", **slot},
            ],
        },
        {
            "id": "g_load",
            "title": "compose loader",
            "col": 1,
            "row": False,
            "sub": "file.go: reads, parses, links services",
            "items": [{"id": "i_load", "text": "Load"}, {"id": "i_link", "text": "linkServices"}],
        },
        {
            "id": "g_jobs",
            "title": "init job check",
            "col": 1,
            "row": True,
            "sub": "initjob.go: lists every bad job"
            if after
            else "initjob.go: stops at the first bad job",
            "items": [{"id": "i_jobs", "text": "normalizeInitJobs"}],
        },
        {
            "id": "g_err",
            "title": "compose errors",
            "col": 2,
            "row": False,
            "sub": "errors.go: new typed errors" if after else "plain text errors only",
            "items": [
                {"id": "e_txt", "text": "text error", "ground": "fmt.Errorf", "tone": "bad"},
                {"id": "e_read", "text": "ReadComposeError", **slot},
                {"id": "e_parse", "text": "ParseComposeError", **slot},
                {"id": "e_val", "text": "ValidateComposeError", **slot},
                {"id": "e_iss", "text": "ValidationIssue", **slot},
            ],
        },
    ]


def arrow(at, frm, to, label=None, tone=None, until=None):
    cue = {"at": at, "do": "arrow", "from": frm, "to": to}
    if label:
        cue["label"] = label
    if tone:
        cue["tone"] = tone
    if until is not None:
        cue["until"] = until
    return cue


title = {
    "type": "title",
    "kicker": "Merged pull request",
    "say": [
        "This pull request changes how the compose loader reports a bad stack file, and adds a faults package.",
    ],
}

before = {
    "type": "groups",
    "groups": groups(after=False),
    "cite": cites(
        "read",
        "read_old",
        "load",
        "reader",
        "txt_read",
        "txt_decode",
        "link_old",
        "jobs_old",
        "jobs_first",
        "t_read",
        "t_parse",
        "t_val",
        "t_issue",
        "f_err",
        "f_tmp",
    ),
    "say": [
        "Before this change, §Load§ reads the stack file and then calls §linkServices§.",
        "Each step returns a text error, and the init job check stops at the first bad job.",
        "The typed errors and the faults package do not exist yet.",
    ],
    "cues": [
        arrow("then calls", "g_load", "g_jobs", "checks init jobs"),
        arrow("Each step returns", "i_load", "e_txt", "text error", "bad"),
        {"at": "stops at the first bad job", "do": "tone", "id": "g_jobs", "tone": "bad"},
        {
            "at": "do not exist yet",
            "do": "show",
            "ids": ["e_read", "e_parse", "e_val", "e_iss", "f_err", "f_tmp"],
            "step": 0.1,
        },
    ],
    "hold": 0.4,
}

after = {
    "type": "groups",
    "groups": groups(after=True, slots=True),
    "cite": cites(
        "read",
        "read_new",
        "load",
        "txt_read",
        "new_read",
        "new_parse",
        "new_decode",
        "link_new",
        "jobs_new",
        "jobs_all",
        "t_read",
        "t_parse",
        "t_val",
        "t_issue",
        "f_err",
        "f_tmp",
    ),
    "say": [
        "After this change, §Load§ returns one of three error types, and each type keeps the file path.",
        "The init job check now collects every bad job as a §ValidationIssue§.",
        "The new faults package adds an §Error§ interface with §Temporary§, and no code calls it yet.",
    ],
    "cues": [
        {"at": "After this change", "do": "strike", "id": "e_txt"},
        {"at": "three error types", "do": "fill", "ids": ["e_read", "e_parse", "e_val"]},
        {"at": "three error types", "do": "tone", "id": "g_err", "tone": "good"},
        {"at": "collects every bad job", "do": "fill", "ids": ["e_iss"]},
        {"at": "collects every bad job", "do": "tone", "id": "g_jobs", "tone": "good"},
        arrow("collects every bad job", "i_jobs", "e_iss", "one issue per job", "good"),
        {"at": "new faults package", "do": "fill", "ids": ["f_err", "f_tmp"]},
        {"at": "new faults package", "do": "tone", "id": "g_faults", "tone": "info"},
        {"at": "no code calls it yet", "do": "mark", "id": "g_faults", "text": "✗", "tone": "info"},
    ],
    "hold": 0.4,
}

walk = {
    "type": "groups",
    "groups": groups(after=True),
    "cite": cites(
        "read",
        "read_new",
        "reader",
        "load",
        "txt_read",
        "new_read",
        "new_parse",
        "new_decode",
        "new_link",
        "link_new",
        "link_name",
        "jobs_new",
        "t_read",
        "t_parse",
        "t_val",
        "t_issue",
        "f_err",
        "f_tmp",
    ),
    "say": [
        "When the stack file is missing, §Load§ returns §ReadComposeError§, and the git §ReadFile§ also adds the path.",
        "When the file holds bad YAML syntax, §Load§ returns §ParseComposeError§.",
        "When a value has a wrong type or a job has no image, §Load§ returns §ValidateComposeError§ with every issue.",
    ],
    "cues": [
        {"at": [0, 0.0], "do": "strike", "id": "e_txt"},
        arrow("stack file is missing", "g_load", "g_err", "returns one type", "bad"),
        {"at": "stack file is missing", "do": "tone", "id": "e_read", "tone": "bad"},
        {"at": "also adds the path", "do": "tone", "id": "g_git", "tone": "good"},
        {"at": "bad YAML syntax", "do": "tone", "id": "e_parse", "tone": "bad"},
        {"at": "wrong type", "do": "tone", "id": "e_val", "tone": "bad"},
        arrow("job has no image", "g_jobs", "g_load", "issues", "bad"),
        {"at": "with every issue", "do": "tone", "id": "e_iss", "tone": "good"},
    ],
    "hold": 0.6,
}

tests = {
    "type": "list",
    "label": "tests this pull request adds",
    "tone": "good",
    "mark": "✓",
    "code": False,
    "items": [
        {"text": "TestFileLoaderReadComposeError", "cite": "internal/compose/errors_test.go:27"},
        {"text": "TestFileLoaderParseComposeError", "cite": "internal/compose/errors_test.go:39"},
        {
            "text": "TestFileLoaderValidateComposeErrorInitJob",
            "cite": "internal/compose/errors_test.go:52",
        },
        {
            "text": "TestFileLoaderValidateComposeErrorWrongType",
            "cite": "internal/compose/errors_test.go:80",
        },
        {
            "text": "TestFileLoaderKeepsIOErrorForReferencedFiles",
            "cite": "internal/compose/errors_test.go:95",
        },
        {"text": "TestComposeErrorsWrap", "cite": "internal/compose/errors_test.go:116"},
        {
            "text": "TestGoGitRepositoryReadFileWrapsOriginalError",
            "cite": "internal/modules/gitops/git/read_file_test.go:12",
        },
    ],
    "more": None,
    "say": [
        "New tests check each error type, the issue list and the path in the git read error.",
    ],
    "cues": [{"at": [0, 0.1], "do": "items", "step": 0.3}],
    "hold": 0.6,
}

outro = {
    "type": "outro",
    "l1": "Compose load errors now carry a type, the file path and every validation issue.",
    "l2": "Start at Load in internal/compose/file.go. No code uses the faults package yet.",
    "nocap": True,
    "say": [
        "Compose load errors now carry a type, the file path and every validation issue.",
    ],
    "cues": [
        {"at": [0, 0.0], "do": "l1"},
        {"at": [0, 0.5], "do": "l2"},
        {"at": [0, 0.9], "do": "cmd"},
    ],
    "hold": 1.0,
}

board = {"name": "pr116-system-view", "scenes": [title, before, after, walk, tests, outro]}
text_out = json.dumps(board, indent=2, ensure_ascii=False).replace("§", "`")
(OUT / "board.json").write_text(text_out + "\n")
print("wrote", OUT / "board.json")
