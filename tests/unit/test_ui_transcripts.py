"""Best-effort reading of Claude Code transcripts for `spado ui`."""

import json
import re

from spado.ui import transcripts

RUN = "5f0c7c1e-9a51-4c43-9e44-7d7f3c1a0b10"
CAOAO = "11111111-2222-4333-8444-555555555555"
CTAO = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
ACTORS = [
    {"id": "human-1", "definition": "Human", "level": "human"},
    {"id": CAOAO, "definition": "CAOAO", "level": "orchestrator"},
    {"id": CTAO, "definition": "CTAO", "level": "officer"},
]


def jsonl(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x) if not isinstance(x, str) else x for x in lines) + "\n")


def session(folder, name="s1", run=RUN):
    main = folder / f"{name}.jsonl"
    jsonl(
        main,
        [
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2026-10-19T09:00:00.000Z",
                "message": {"role": "user", "content": "/spdlc --new-run --phase idea-strategy"},
            },
            "{not json",
            {
                "type": "assistant",
                "uuid": "a1",
                "timestamp": "2026-10-19T09:01:00.000Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": f"Created run {run}."},
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "Agent",
                            "input": {
                                "subagent_type": "caoao",
                                "description": "Coordinate phase 1",
                                "prompt": f"Run {run}. SPADO_ACTOR_TOKEN_FILE=/p/.spado/local/actors/{CAOAO}.token",
                            },
                        },
                    ],
                },
            },
            {
                "type": "user",
                "uuid": "u2",
                "timestamp": "2026-10-19T09:02:00.000Z",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "toolu_1", "content": "done"}
                    ],
                },
            },
        ],
    )
    sub = folder / name / "subagents" / "agent-abc.jsonl"
    jsonl(
        sub,
        [
            {
                "type": "user",
                "isSidechain": True,
                "timestamp": "2026-10-19T09:01:05.000Z",
                "message": {"role": "user", "content": "Coordinate"},
            },
            {
                "type": "assistant",
                "isSidechain": True,
                "uuid": "s1",
                "timestamp": "2026-10-19T09:01:30.000Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_9",
                            "name": "Bash",
                            "input": {"command": f"spado actor create CTAO --run {run}"},
                        },
                    ],
                },
            },
            {
                "type": "assistant",
                "isSidechain": True,
                "timestamp": "2026-10-19T09:01:50.000Z",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Delegated CTAO and prepared the plan."}],
                },
            },
        ],
    )
    sub.with_suffix(".meta.json").write_text(
        json.dumps(
            {"agentType": "caoao", "description": "Coordinate phase 1", "toolUseId": "toolu_1"}
        )
    )


def test_project_dir_uses_claude_encoding_or_cwd(tmp_path):
    base = tmp_path / "projects"
    root = tmp_path / "my.product"
    root.mkdir()
    # Claude Code replaces every non-alphanumeric character with "-".
    encoded = base / re.sub(r"[^A-Za-z0-9]", "-", str(root.resolve()))
    encoded.mkdir(parents=True)
    assert transcripts.project_dir(root, base) == encoded
    encoded.rmdir()
    other = base / "renamed"
    jsonl(other / "x.jsonl", [{"cwd": str(root.resolve()), "type": "user"}])
    assert transcripts.project_dir(root, base) == other
    assert transcripts.project_dir(tmp_path / "missing", tmp_path / "nowhere") is None


def test_reads_prompts_delegations_threads_and_links_actors(tmp_path):
    session(tmp_path)
    session(tmp_path, name="unrelated", run="00000000-0000-4000-8000-000000000000")
    result = transcripts.read(tmp_path, RUN, ACTORS)
    assert result["available"] and result["sessions"] == ["s1"]
    kinds = [e["kind"] for e in result["entries"]]
    assert kinds.count("human_prompt") == 1  # tool results are not Human prompts
    prompt = next(e for e in result["entries"] if e["kind"] == "human_prompt")
    assert prompt["from"] == "human-1" and prompt["to"] == [transcripts.HOST]
    delegation = next(e for e in result["entries"] if e["kind"] == "delegation_prompt")
    assert delegation["to"] == [CAOAO]  # linked through the token path in the prompt
    assert "SPADO_ACTOR_TOKEN_FILE" in delegation["text"]
    command = next(e for e in result["entries"] if e["kind"] == "spado_command")
    assert command["from"] == CAOAO and command["summary"].startswith("spado actor create")
    report = next(e for e in result["entries"] if e["kind"] == "subagent_report")
    assert report["text"] == "Delegated CTAO and prepared the plan."
    [thread] = result["threads"]
    assert thread["actor"] == CAOAO and [m["role"] for m in thread["messages"]] == [
        "user",
        "tool",
        "assistant",
    ]


def test_falls_back_to_role_name_and_marks_unlinked_agents(tmp_path):
    session(tmp_path)
    meta = tmp_path / "s1" / "subagents" / "agent-abc.meta.json"
    main = tmp_path / "s1.jsonl"
    main.write_text(main.read_text().replace(f"actors/{CAOAO}.token", "no-token"))
    assert transcripts.read(tmp_path, RUN, ACTORS)["threads"][0]["actor"] == CAOAO
    main.write_text(
        main.read_text().replace('"subagent_type": "caoao"', '"subagent_type": "explorer"')
    )
    meta.write_text(json.dumps({"agentType": "explorer", "toolUseId": "toolu_1"}))
    assert transcripts.read(tmp_path, RUN, ACTORS)["threads"][0]["actor"] == "agent:agent-abc"


def test_missing_folder_is_reported_not_raised():
    assert transcripts.read(None, RUN, ACTORS) == {
        "available": False,
        "folder": None,
        "entries": [],
        "threads": [],
    }
