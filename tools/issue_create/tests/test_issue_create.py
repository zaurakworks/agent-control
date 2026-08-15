from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Sequence


MODULE_PATH = Path(__file__).resolve().parents[1] / "issue_create.py"
SPEC = importlib.util.spec_from_file_location("issue_create", MODULE_PATH)
assert SPEC and SPEC.loader
issue_create = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = issue_create
SPEC.loader.exec_module(issue_create)


SKILL_TABLE = """
## 三、任何路径新建 Issue 的共享骨架

| 标题前缀 | 类型 label | 经营节点 | 使用执行状态 |
| --- | --- | --- | --- |
| `目标：` | `类型/目标` | 目标／诉求 | 否 |
| `诉求：` | `类型/诉求` | 目标／诉求 | 否 |
| `交付：` | `类型/交付` | 交付任务 | 是 |
| `实验：` | `类型/实验` | 计划／实验 | 是 |
| `调研：` | `类型/调研` | 计划／实验 | 是 |
| `摩擦：` | `类型/摩擦` | 能力缺口 | 否 |
| `方案：` | `类型/方案` | 计划／实验 | 是 |
"""


VALID_BODY = """## 来源、父级与授权链

来源可核验。

## 范围

仅作自验。

## 验收条件

远端字段逐项一致。
"""


class FakeGitHub:
    def __init__(self, *, fail_step: str | None = None) -> None:
        self.fail_step = fail_step
        self.calls: list[str] = []

    def repository_context(
        self, repository: str, type_label: str, domain_label: str
    ) -> dict[str, Any]:
        self.calls.append("repository")
        return {
            "id": "R_repo",
            "nameWithOwner": repository,
            "labels": {type_label: "L_type", domain_label: "L_domain"},
        }

    def project_context(self, project_id: str) -> dict[str, Any]:
        self.calls.append("project")
        return {
            "id": project_id,
            "owner": "zaurakworks",
            "number": 1,
            "title": "运营台",
            "statusFieldId": "F_status",
            "statusOptions": {
                "Todo": "opt_todo",
                "In Progress": "opt_progress",
                "Done": "opt_done",
            },
        }

    def parent_issue(self, repository: str, number: int) -> dict[str, Any]:
        self.calls.append("parent_preflight")
        return {"id": "I_parent", "number": number, "title": "父级", "url": "u/1"}

    def create_issue(
        self,
        repository_id: str,
        title: str,
        body: str,
        label_ids: Sequence[str],
    ) -> dict[str, Any]:
        self.calls.append("create")
        self.title = title
        self.body = body
        return {"id": "I_child", "number": 2, "title": title, "url": "u/2"}

    def add_project_item(self, project_id: str, issue_id: str) -> dict[str, Any]:
        self.calls.append("project_add")
        if self.fail_step == "project_add":
            raise issue_create.IssueCreateError("project unavailable")
        return {"id": "PVTI_item"}

    def set_project_status(
        self,
        project_id: str,
        item_id: str,
        field_id: str,
        option_id: str,
    ) -> None:
        self.calls.append("status")
        if self.fail_step == "status":
            raise issue_create.IssueCreateError("status unavailable")

    def add_sub_issue(self, parent_id: str, child_id: str) -> None:
        self.calls.append("subissue")
        if self.fail_step == "subissue":
            raise issue_create.IssueCreateError("relationship unavailable")

    def reread_issue(self, issue_id: str, project_item_id: str) -> dict[str, Any]:
        self.calls.append("reread")
        return {
            "id": issue_id,
            "number": 2,
            "url": "u/2",
            "title": self.title,
            "body": self.body,
            "labels": {
                "nodes": [
                    {"id": "L_type", "name": "类型/调研"},
                    {"id": "L_domain", "name": "领域/横向"},
                ]
            },
            "parent": {"id": "I_parent", "number": 1, "title": "父级", "url": "u/1"},
            "createdProjectItem": {
                "id": project_item_id,
                "project": {
                    "id": issue_create.DEFAULT_PROJECT_ID,
                    "number": 1,
                    "title": "运营台",
                },
                "content": {"id": issue_id, "number": 2, "title": self.title},
                "fieldValues": {
                    "nodes": [
                        {
                            "optionId": "opt_progress",
                            "name": "In Progress",
                            "field": {"id": "F_status", "name": "Status"},
                        }
                    ]
                },
            },
        }


def load_rules() -> tuple[Path, dict[str, Any]]:
    temporary = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".md", delete=False
    )
    try:
        temporary.write(SKILL_TABLE)
        temporary.close()
        path = Path(temporary.name)
        return path, issue_create.parse_type_rules(path)
    except Exception:
        temporary.close()
        raise


class LocalValidationTests(unittest.TestCase):
    def test_parses_the_mapping_from_the_skill_table(self) -> None:
        path, rules = load_rules()
        self.addCleanup(path.unlink, missing_ok=True)
        self.assertEqual(rules["调研"].prefix, "调研：")
        self.assertEqual(rules["调研"].label, "类型/调研")
        self.assertEqual(rules["调研"].operating_node, "计划／实验")
        self.assertTrue(rules["调研"].uses_execution_status)
        self.assertFalse(rules["摩擦"].uses_execution_status)

    def test_rejects_handwritten_allowed_or_invented_prefix(self) -> None:
        for title in ("调研：重复前缀", "清单：闭集外前缀", "专项: 闭集外前缀"):
            with self.subTest(title=title), self.assertRaises(issue_create.IssueCreateError):
                issue_create.validate_short_title(title)

    def test_requires_all_body_sections(self) -> None:
        with self.assertRaisesRegex(issue_create.IssueCreateError, "验收条件"):
            issue_create.validate_body(
                "## 来源、父级与授权链\n来源\n\n## 范围\n范围\n"
            )

    def test_rejects_every_github_closing_keyword_even_when_negated(self) -> None:
        for keyword in (
            "close",
            "closes",
            "closed",
            "fix",
            "fixes",
            "fixed",
            "resolve",
            "resolves",
            "resolved",
        ):
            with self.subTest(keyword=keyword), self.assertRaises(
                issue_create.IssueCreateError
            ):
                issue_create.validate_body(VALID_BODY + f"\n不 {keyword} #123\n")

    def test_status_is_required_or_forbidden_from_skill_row(self) -> None:
        path, rules = load_rules()
        self.addCleanup(path.unlink, missing_ok=True)
        project = FakeGitHub().project_context(issue_create.DEFAULT_PROJECT_ID)
        status = issue_create.resolve_status("进行中", rules["调研"], project)
        self.assertEqual(status["name"], "In Progress")
        with self.assertRaisesRegex(issue_create.IssueCreateError, "required"):
            issue_create.resolve_status(None, rules["调研"], project)
        with self.assertRaisesRegex(issue_create.IssueCreateError, "remain blank"):
            issue_create.resolve_status("Todo", rules["摩擦"], project)


class WorkflowTests(unittest.TestCase):
    def request(self) -> Any:
        return issue_create.CreateRequest(
            issue_type="调研",
            domain="横向",
            short_title="CLI 自验，可关闭",
            body=VALID_BODY,
            repository=issue_create.DEFAULT_REPOSITORY,
            parent_number=1,
            requested_status="进行中",
            project_id=issue_create.DEFAULT_PROJECT_ID,
        )

    def test_writes_and_rereads_the_complete_batch(self) -> None:
        path, rules = load_rules()
        self.addCleanup(path.unlink, missing_ok=True)
        github = FakeGitHub()
        report = issue_create.create_and_verify(
            self.request(), rules, github, skill_file=path
        )
        self.assertTrue(report["ok"])
        self.assertTrue(all(report["verification"].values()))
        self.assertEqual(
            github.calls,
            [
                "repository",
                "project",
                "parent_preflight",
                "create",
                "project_add",
                "status",
                "subissue",
                "reread",
            ],
        )

    def test_partial_success_stops_without_recreating(self) -> None:
        path, rules = load_rules()
        self.addCleanup(path.unlink, missing_ok=True)
        github = FakeGitHub(fail_step="subissue")
        with self.assertRaises(issue_create.PartialSuccessError) as caught:
            issue_create.create_and_verify(
                self.request(), rules, github, skill_file=path
            )
        report = caught.exception.report
        self.assertEqual(report["createdIssue"]["id"], "I_child")
        self.assertEqual(report["failedStep"], "addSubIssue")
        self.assertEqual(github.calls.count("create"), 1)
        self.assertNotIn("reread", github.calls)


class GraphQLContractTests(unittest.TestCase):
    def test_sub_issue_mutation_carries_the_required_feature_header(self) -> None:
        client = issue_create.GhClient()
        captured: dict[str, Any] = {}

        def record(
            query: str,
            variables: dict[str, Any],
            *,
            headers: dict[str, str] | None = None,
        ) -> dict[str, Any]:
            captured.update(
                {"query": query, "variables": variables, "headers": headers}
            )
            return {}

        client.graphql = record  # type: ignore[method-assign]
        client.add_sub_issue("I_parent", "I_child")
        self.assertIn("addSubIssue", captured["query"])
        self.assertEqual(
            captured["variables"],
            {"parentId": "I_parent", "childId": "I_child"},
        )
        self.assertEqual(
            captured["headers"], {"GraphQL-Features": "sub_issues"}
        )

    def test_status_mutation_updates_an_item_value_not_the_field_definition(self) -> None:
        client = issue_create.GhClient()
        captured: dict[str, Any] = {}

        def record(
            query: str,
            variables: dict[str, Any],
            *,
            headers: dict[str, str] | None = None,
        ) -> dict[str, Any]:
            captured.update({"query": query, "variables": variables})
            return {}

        client.graphql = record  # type: ignore[method-assign]
        client.set_project_status("P", "I", "F", "O")
        self.assertIn("updateProjectV2ItemFieldValue", captured["query"])
        self.assertNotIn("updateProjectV2Field(", captured["query"])


if __name__ == "__main__":
    unittest.main()
