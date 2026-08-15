#!/usr/bin/env python3
"""Create one GitHub Issue through the repository's mandatory creation skeleton."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence


TYPE_CHOICES = ("目标", "诉求", "交付", "实验", "调研", "摩擦", "方案")
DOMAIN_CHOICES = (
    "总目标",
    "知识",
    "长程工作",
    "思考方法",
    "协同协作",
    "资源运营",
    "横向",
)
REQUIRED_SECTIONS = (
    "来源、父级与授权链",
    "范围",
    "验收条件",
)
DEFAULT_REPOSITORY = "Eridanus117/agent-control"
DEFAULT_PROJECT_ID = "PVT_kwHOEua8Pc4BgZbR"
SKILL_RELATIVE_PATH = Path(
    "plugins/github-collaboration/skills/objective-to-issues/SKILL.md"
)
SKILL_CACHE_RELATIVE_PATH = Path("skills/objective-to-issues/SKILL.md")
TYPE_TABLE_ROW = re.compile(
    r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*(是|否)\s*\|\s*$",
    re.MULTILINE,
)
CLOSING_KEYWORD = re.compile(
    r"\b(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\b",
    re.IGNORECASE,
)
HANDWRITTEN_PREFIX = re.compile(r"^\s*[^：:\r\n]+[：:]")
REPOSITORY_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
STATUS_ALIASES = {
    "待办": "Todo",
    "进行中": "In Progress",
    "完成": "Done",
}


class IssueCreateError(RuntimeError):
    """Raised before creation, or when a GitHub call cannot be trusted."""


class PartialSuccessError(IssueCreateError):
    """Raised after the Issue exists and a later step fails."""

    def __init__(self, report: dict[str, Any]) -> None:
        super().__init__(str(report.get("error") or "Issue creation partially succeeded"))
        self.report = report


@dataclass(frozen=True)
class TypeRule:
    prefix: str
    label: str
    operating_node: str
    uses_execution_status: bool


@dataclass(frozen=True)
class CreateRequest:
    issue_type: str
    domain: str
    short_title: str
    body: str
    repository: str
    parent_number: int | None
    requested_status: str | None
    project_id: str


class GitHubPort(Protocol):
    def repository_context(
        self, repository: str, type_label: str, domain_label: str
    ) -> dict[str, Any]: ...

    def project_context(self, project_id: str) -> dict[str, Any]: ...

    def parent_issue(self, repository: str, number: int) -> dict[str, Any]: ...

    def create_issue(
        self,
        repository_id: str,
        title: str,
        body: str,
        label_ids: Sequence[str],
    ) -> dict[str, Any]: ...

    def add_project_item(self, project_id: str, issue_id: str) -> dict[str, Any]: ...

    def set_project_status(
        self,
        project_id: str,
        item_id: str,
        field_id: str,
        option_id: str,
    ) -> None: ...

    def add_sub_issue(self, parent_id: str, child_id: str) -> None: ...

    def reread_issue(self, issue_id: str, project_item_id: str) -> dict[str, Any]: ...


class GhClient:
    """Small, no-retry GraphQL client using the authenticated GitHub CLI."""

    def __init__(self, timeout_seconds: float = 45.0) -> None:
        self.timeout_seconds = timeout_seconds

    def graphql(
        self,
        query: str,
        variables: Mapping[str, Any],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        command = ["gh", "api", "graphql"]
        for name, value in (headers or {}).items():
            command.extend(["-H", f"{name}: {value}"])
        command.extend(["--input", "-"])
        payload = json.dumps(
            {"query": query, "variables": dict(variables)}, ensure_ascii=False
        )
        try:
            completed = subprocess.run(
                command,
                input=payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as error:
            raise IssueCreateError("gh CLI not found") from error
        except subprocess.TimeoutExpired as error:
            raise IssueCreateError(
                f"GitHub GraphQL call timed out after {self.timeout_seconds:g}s"
            ) from error

        output = (completed.stdout or "").strip()
        if completed.returncode:
            detail = (completed.stderr or output or "unknown gh error").strip()
            raise IssueCreateError(f"GitHub GraphQL call failed: {detail[:600]}")
        try:
            response = json.loads(output)
        except json.JSONDecodeError as error:
            raise IssueCreateError(
                f"GitHub GraphQL returned invalid JSON: {output[:300] or 'no output'}"
            ) from error
        if response.get("errors"):
            raise IssueCreateError(
                "GitHub GraphQL returned errors: "
                + json.dumps(response["errors"], ensure_ascii=False)
            )
        data = response.get("data")
        if not isinstance(data, dict):
            raise IssueCreateError("GitHub GraphQL returned no data object")
        return data

    def repository_context(
        self, repository: str, type_label: str, domain_label: str
    ) -> dict[str, Any]:
        owner, name = split_repository(repository)
        data = self.graphql(
            """
            query($owner: String!, $name: String!, $typeLabel: String!, $domainLabel: String!) {
              repository(owner: $owner, name: $name) {
                id
                nameWithOwner
                typeLabels: labels(first: 20, query: $typeLabel) { nodes { id name } }
                domainLabels: labels(first: 20, query: $domainLabel) { nodes { id name } }
              }
            }
            """,
            {
                "owner": owner,
                "name": name,
                "typeLabel": type_label,
                "domainLabel": domain_label,
            },
        )
        repository_data = data.get("repository")
        if not isinstance(repository_data, dict):
            raise IssueCreateError(f"repository not found or inaccessible: {repository}")

        labels: dict[str, str] = {}
        for connection_name, expected in (
            ("typeLabels", type_label),
            ("domainLabels", domain_label),
        ):
            nodes = (repository_data.get(connection_name) or {}).get("nodes") or []
            exact = [node for node in nodes if node.get("name") == expected]
            if len(exact) != 1:
                raise IssueCreateError(
                    f"governance gap: repository {repository} is missing required label "
                    f"{expected!r}; do not create a synonym"
                )
            labels[expected] = str(exact[0]["id"])
        return {
            "id": str(repository_data["id"]),
            "nameWithOwner": str(repository_data["nameWithOwner"]),
            "labels": labels,
        }

    def project_context(self, project_id: str) -> dict[str, Any]:
        data = self.graphql(
            """
            query($projectId: ID!) {
              node(id: $projectId) {
                ... on ProjectV2 {
                  id
                  number
                  title
                  owner { ... on Organization { login } ... on User { login } }
                  fields(first: 100) {
                    nodes {
                      ... on ProjectV2Field { id name dataType }
                      ... on ProjectV2SingleSelectField {
                        id name dataType options { id name }
                      }
                      ... on ProjectV2IterationField { id name dataType }
                    }
                  }
                }
              }
            }
            """,
            {"projectId": project_id},
        )
        project = data.get("node")
        if not isinstance(project, dict) or project.get("id") != project_id:
            raise IssueCreateError(f"ProjectV2 not found or inaccessible: {project_id}")
        fields = (project.get("fields") or {}).get("nodes") or []
        status_fields = [
            field
            for field in fields
            if field.get("name") == "Status" and field.get("dataType") == "SINGLE_SELECT"
        ]
        if len(status_fields) != 1:
            raise IssueCreateError(
                f"governance gap: Project {project_id} must have exactly one single-select Status field"
            )
        status_field = status_fields[0]
        options = {
            str(option["name"]): str(option["id"])
            for option in status_field.get("options") or []
        }
        return {
            "id": str(project["id"]),
            "number": project.get("number"),
            "title": project.get("title"),
            "owner": (project.get("owner") or {}).get("login"),
            "statusFieldId": str(status_field["id"]),
            "statusOptions": options,
        }

    def parent_issue(self, repository: str, number: int) -> dict[str, Any]:
        owner, name = split_repository(repository)
        data = self.graphql(
            """
            query($owner: String!, $name: String!, $number: Int!) {
              repository(owner: $owner, name: $name) {
                issue(number: $number) { id number title url }
              }
            }
            """,
            {"owner": owner, "name": name, "number": number},
        )
        issue = ((data.get("repository") or {}).get("issue"))
        if not isinstance(issue, dict):
            raise IssueCreateError(
                f"parent Issue not found in {repository}: #{number}"
            )
        return dict(issue)

    def create_issue(
        self,
        repository_id: str,
        title: str,
        body: str,
        label_ids: Sequence[str],
    ) -> dict[str, Any]:
        data = self.graphql(
            """
            mutation($repositoryId: ID!, $title: String!, $body: String!, $labelIds: [ID!]) {
              createIssue(input: {
                repositoryId: $repositoryId,
                title: $title,
                body: $body,
                labelIds: $labelIds
              }) {
                issue { id number title url }
              }
            }
            """,
            {
                "repositoryId": repository_id,
                "title": title,
                "body": body,
                "labelIds": list(label_ids),
            },
        )
        issue = ((data.get("createIssue") or {}).get("issue"))
        if not isinstance(issue, dict):
            raise IssueCreateError("createIssue returned no Issue")
        return dict(issue)

    def add_project_item(self, project_id: str, issue_id: str) -> dict[str, Any]:
        data = self.graphql(
            """
            mutation($projectId: ID!, $contentId: ID!) {
              addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
                item { id }
              }
            }
            """,
            {"projectId": project_id, "contentId": issue_id},
        )
        item = ((data.get("addProjectV2ItemById") or {}).get("item"))
        if not isinstance(item, dict):
            raise IssueCreateError("addProjectV2ItemById returned no Project item")
        return dict(item)

    def set_project_status(
        self,
        project_id: str,
        item_id: str,
        field_id: str,
        option_id: str,
    ) -> None:
        self.graphql(
            """
            mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
              updateProjectV2ItemFieldValue(input: {
                projectId: $projectId,
                itemId: $itemId,
                fieldId: $fieldId,
                value: {singleSelectOptionId: $optionId}
              }) { projectV2Item { id } }
            }
            """,
            {
                "projectId": project_id,
                "itemId": item_id,
                "fieldId": field_id,
                "optionId": option_id,
            },
        )

    def add_sub_issue(self, parent_id: str, child_id: str) -> None:
        self.graphql(
            """
            mutation($parentId: ID!, $childId: ID!) {
              addSubIssue(input: {issueId: $parentId, subIssueId: $childId}) {
                issue { id }
                subIssue { id }
              }
            }
            """,
            {"parentId": parent_id, "childId": child_id},
            headers={"GraphQL-Features": "sub_issues"},
        )

    def reread_issue(self, issue_id: str, project_item_id: str) -> dict[str, Any]:
        data = self.graphql(
            """
            query($issueId: ID!, $projectItemId: ID!) {
              issue: node(id: $issueId) {
                ... on Issue {
                  id number title body url
                  labels(first: 100) { nodes { id name } }
                  parent { id number title url }
                }
              }
              projectItem: node(id: $projectItemId) {
                ... on ProjectV2Item {
                  id
                  project { id number title }
                  content { ... on Issue { id number title url } }
                  fieldValues(first: 100) {
                    nodes {
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        optionId
                        name
                        field { ... on ProjectV2SingleSelectField { id name } }
                      }
                      ... on ProjectV2ItemFieldTextValue {
                        text
                        field { ... on ProjectV2Field { id name } }
                      }
                    }
                  }
                }
              }
            }
            """,
            {"issueId": issue_id, "projectItemId": project_item_id},
        )
        issue = data.get("issue")
        if not isinstance(issue, dict):
            raise IssueCreateError(f"created Issue cannot be reread: {issue_id}")
        project_item = data.get("projectItem")
        if not isinstance(project_item, dict):
            raise IssueCreateError(
                f"created Project item cannot be reread: {project_item_id}"
            )
        result = dict(issue)
        result["createdProjectItem"] = dict(project_item)
        return result


def split_repository(repository: str) -> tuple[str, str]:
    if not REPOSITORY_NAME.fullmatch(repository):
        raise IssueCreateError(
            f"invalid --repo {repository!r}; expected OWNER/NAME"
        )
    owner, name = repository.split("/", 1)
    return owner, name


def skill_candidates(explicit: Path | None) -> list[Path]:
    if explicit is not None:
        return [explicit]
    candidates: list[Path] = []
    exact = os.environ.get("OBJECTIVE_TO_ISSUES_SKILL")
    if exact:
        candidates.append(Path(exact))
    root = os.environ.get("AGENT_PLUGINS_ROOT")
    if root:
        candidates.append(Path(root) / SKILL_RELATIVE_PATH)
    candidates.append(Path.home() / "workspace" / "agent-plugins" / SKILL_RELATIVE_PATH)
    cache_root = Path.home() / ".codex" / "plugins" / "cache" / "agent-plugins"
    if cache_root.is_dir():
        candidates.extend(
            sorted(
                cache_root.glob(f"*/{SKILL_CACHE_RELATIVE_PATH.as_posix()}"),
                reverse=True,
            )
        )
    return candidates


def resolve_skill_file(explicit: Path | None) -> Path:
    candidates = skill_candidates(explicit)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    rendered = ", ".join(str(path) for path in candidates) or "no candidates"
    raise IssueCreateError(
        "cannot locate objective-to-issues SKILL.md; pass --skill-file or set "
        f"OBJECTIVE_TO_ISSUES_SKILL. Checked: {rendered}"
    )


def parse_type_rules(skill_file: Path) -> dict[str, TypeRule]:
    try:
        text = skill_file.read_text(encoding="utf-8")
    except OSError as error:
        raise IssueCreateError(f"cannot read Skill source {skill_file}: {error}") from error
    rules: dict[str, TypeRule] = {}
    for prefix, label, operating_node, uses_status in TYPE_TABLE_ROW.findall(text):
        issue_type = prefix.removesuffix("：")
        if issue_type not in TYPE_CHOICES:
            continue
        if issue_type in rules:
            raise IssueCreateError(
                f"duplicate type row for {issue_type!r} in Skill source {skill_file}"
            )
        rules[issue_type] = TypeRule(
            prefix=prefix,
            label=label,
            operating_node=operating_node.strip(),
            uses_execution_status=uses_status == "是",
        )
    if set(rules) != set(TYPE_CHOICES):
        missing = sorted(set(TYPE_CHOICES) - set(rules))
        extra = sorted(set(rules) - set(TYPE_CHOICES))
        raise IssueCreateError(
            "objective-to-issues type table does not match the CLI closed set; "
            f"missing={missing}, extra={extra}, source={skill_file}"
        )
    for issue_type, rule in rules.items():
        if rule.prefix != f"{issue_type}：" or rule.label != f"类型/{issue_type}":
            raise IssueCreateError(
                f"classification conflict in Skill row for {issue_type}: "
                f"prefix={rule.prefix!r}, label={rule.label!r}"
            )
    return rules


def validate_short_title(title: str) -> str:
    stripped = title.strip()
    if not stripped:
        raise IssueCreateError("--title must not be empty")
    if "\n" in stripped or "\r" in stripped:
        raise IssueCreateError("--title must be one line")
    match = HANDWRITTEN_PREFIX.match(stripped)
    if match:
        raise IssueCreateError(
            f"--title must not contain a handwritten prefix ({match.group(0).strip()!r}); "
            "the prefix is derived from --type"
        )
    return stripped


def validate_body(body: str) -> None:
    missing = [
        section
        for section in REQUIRED_SECTIONS
        if not re.search(rf"^##\s+{re.escape(section)}\s*$", body, re.MULTILINE)
    ]
    if missing:
        raise IssueCreateError(
            "--body-file is missing required sections: " + ", ".join(missing)
        )
    keyword = CLOSING_KEYWORD.search(body)
    if keyword:
        raise IssueCreateError(
            "--body-file contains forbidden GitHub closing keyword "
            f"{keyword.group(0)!r}; negated forms are forbidden too"
        )


def read_body(path: Path) -> str:
    try:
        body = path.read_text(encoding="utf-8-sig")
    except OSError as error:
        raise IssueCreateError(f"cannot read --body-file {path}: {error}") from error
    validate_body(body)
    return body


def resolve_status(
    requested: str | None,
    rule: TypeRule,
    project: Mapping[str, Any],
) -> dict[str, str] | None:
    if not rule.uses_execution_status:
        if requested:
            raise IssueCreateError(
                f"type maps to operating node {rule.operating_node!r}, whose Status must "
                "remain blank; omit --status"
            )
        return None
    if not requested:
        raise IssueCreateError(
            f"type maps to operating node {rule.operating_node!r}, so --status is required"
        )
    options = project.get("statusOptions") or {}
    canonical = requested if requested in options else STATUS_ALIASES.get(requested)
    if not canonical or canonical not in options:
        raise IssueCreateError(
            f"Project has no Status option matching {requested!r}; available options: "
            + ", ".join(sorted(options))
        )
    return {
        "requested": requested,
        "name": canonical,
        "optionId": str(options[canonical]),
    }


def _partial(
    issue: Mapping[str, Any],
    completed_steps: Sequence[str],
    failed_step: str,
    error: Exception | str,
    *,
    project_item: Mapping[str, Any] | None = None,
) -> PartialSuccessError:
    return PartialSuccessError(
        {
            "ok": False,
            "partial": True,
            "createdIssue": dict(issue),
            "projectItem": dict(project_item) if project_item else None,
            "completedSteps": list(completed_steps),
            "failedStep": failed_step,
            "error": str(error),
            "recovery": "inspect and repair this same Issue; do not create a replacement",
        }
    )


def verify_readback(
    readback: Mapping[str, Any],
    *,
    expected_title: str,
    expected_body: str,
    type_label: str,
    domain_label: str,
    project: Mapping[str, Any],
    project_item_id: str,
    expected_status: Mapping[str, str] | None,
    expected_parent: Mapping[str, Any] | None,
) -> dict[str, Any]:
    label_names = [
        str(node.get("name"))
        for node in ((readback.get("labels") or {}).get("nodes") or [])
    ]
    type_dimensions = sorted(name for name in label_names if name.startswith("类型/"))
    domain_dimensions = sorted(name for name in label_names if name.startswith("领域/"))
    item = readback.get("createdProjectItem")
    status_values = []
    if isinstance(item, dict):
        status_values = [
            value
            for value in ((item.get("fieldValues") or {}).get("nodes") or [])
            if (value.get("field") or {}).get("id") == project.get("statusFieldId")
        ]
    parent = readback.get("parent")
    checks = {
        "title": readback.get("title") == expected_title,
        "body": readback.get("body") == expected_body,
        "typeLabel": type_dimensions == [type_label],
        "domainLabel": domain_dimensions == [domain_label],
        "projectItem": bool(
            isinstance(item, dict)
            and item.get("id") == project_item_id
            and (item.get("project") or {}).get("id") == project.get("id")
            and (item.get("content") or {}).get("id") == readback.get("id")
        ),
        "status": (
            len(status_values) == 1
            and status_values[0].get("optionId") == expected_status.get("optionId")
            and status_values[0].get("name") == expected_status.get("name")
            if expected_status
            else len(status_values) == 0
        ),
        "parent": (
            bool(parent and parent.get("id") == expected_parent.get("id"))
            if expected_parent
            else parent is None
        ),
    }
    return {
        "checks": checks,
        "labelNames": label_names,
        "projectItem": item,
        "statusValues": status_values,
        "parent": parent,
        "allMatched": all(checks.values()),
    }


def create_and_verify(
    request: CreateRequest,
    type_rules: Mapping[str, TypeRule],
    github: GitHubPort,
    *,
    skill_file: Path,
) -> dict[str, Any]:
    rule = type_rules[request.issue_type]
    type_label = rule.label
    domain_label = f"领域/{request.domain}"
    title = rule.prefix + request.short_title

    repository = github.repository_context(
        request.repository, type_label, domain_label
    )
    project = github.project_context(request.project_id)
    status = resolve_status(request.requested_status, rule, project)
    parent = (
        github.parent_issue(request.repository, request.parent_number)
        if request.parent_number is not None
        else None
    )

    issue = github.create_issue(
        str(repository["id"]),
        title,
        request.body,
        [
            str(repository["labels"][type_label]),
            str(repository["labels"][domain_label]),
        ],
    )
    completed_steps = ["createIssue"]
    project_item: dict[str, Any] | None = None

    try:
        project_item = github.add_project_item(project["id"], issue["id"])
        completed_steps.append("addProjectV2ItemById")
    except Exception as error:
        raise _partial(issue, completed_steps, "addProjectV2ItemById", error) from error

    if status:
        try:
            github.set_project_status(
                project["id"],
                project_item["id"],
                project["statusFieldId"],
                status["optionId"],
            )
            completed_steps.append("updateProjectV2ItemFieldValue(Status)")
        except Exception as error:
            raise _partial(
                issue,
                completed_steps,
                "updateProjectV2ItemFieldValue(Status)",
                error,
                project_item=project_item,
            ) from error

    if parent:
        try:
            github.add_sub_issue(str(parent["id"]), str(issue["id"]))
            completed_steps.append("addSubIssue")
        except Exception as error:
            raise _partial(
                issue,
                completed_steps,
                "addSubIssue",
                error,
                project_item=project_item,
            ) from error

    try:
        readback = github.reread_issue(
            str(issue["id"]), str(project_item["id"])
        )
        verification = verify_readback(
            readback,
            expected_title=title,
            expected_body=request.body,
            type_label=type_label,
            domain_label=domain_label,
            project=project,
            project_item_id=str(project_item["id"]),
            expected_status=status,
            expected_parent=parent,
        )
    except Exception as error:
        raise _partial(
            issue,
            completed_steps,
            "remoteReadback",
            error,
            project_item=project_item,
        ) from error
    if not verification["allMatched"]:
        mismatches = [
            name for name, matched in verification["checks"].items() if not matched
        ]
        raise _partial(
            issue,
            completed_steps,
            "remoteReadbackComparison",
            "mismatched fields: " + ", ".join(mismatches),
            project_item=project_item,
        )
    completed_steps.append("remoteReadbackComparison")

    return {
        "ok": True,
        "issue": {
            "id": readback.get("id"),
            "number": readback.get("number"),
            "url": readback.get("url"),
            "title": readback.get("title"),
            "body": readback.get("body"),
        },
        "classification": {
            "type": request.issue_type,
            "typeLabel": type_label,
            "domain": request.domain,
            "domainLabel": domain_label,
            "operatingNode": rule.operating_node,
            "usesExecutionStatus": rule.uses_execution_status,
            "skillSource": str(skill_file),
        },
        "project": {
            "id": project.get("id"),
            "owner": project.get("owner"),
            "number": project.get("number"),
            "title": project.get("title"),
            "itemId": project_item.get("id"),
            "status": status,
            "remoteItem": verification.get("projectItem"),
            "remoteStatusValues": verification.get("statusValues"),
        },
        "parent": verification.get("parent"),
        "labels": verification.get("labelNames"),
        "verification": verification.get("checks"),
        "completedSteps": completed_steps,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--type",
        dest="issue_type",
        required=True,
        choices=TYPE_CHOICES,
        help="closed Issue type; the title prefix and type label are derived from it",
    )
    parser.add_argument(
        "--domain",
        required=True,
        choices=DOMAIN_CHOICES,
        help="closed domain dimension; 领域/<value> must already exist",
    )
    parser.add_argument(
        "--title",
        required=True,
        help="one-line short title without any handwritten prefix",
    )
    parser.add_argument("--body-file", required=True, type=Path)
    parser.add_argument("--parent", type=int, help="native parent Issue number")
    parser.add_argument(
        "--status",
        help=(
            "required only for types whose Skill row uses execution status; accepts an "
            "exact Project option or 待办/进行中/完成"
        ),
    )
    parser.add_argument("--repo", default=DEFAULT_REPOSITORY)
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument(
        "--skill-file",
        type=Path,
        help="override the runtime objective-to-issues SKILL.md source",
    )
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        skill_file = resolve_skill_file(args.skill_file)
        rules = parse_type_rules(skill_file)
        title = validate_short_title(args.title)
        body = read_body(args.body_file)
        repository = "/".join(split_repository(args.repo))
        if args.parent is not None and args.parent <= 0:
            raise IssueCreateError("--parent must be a positive Issue number")
        if args.timeout_seconds <= 0:
            raise IssueCreateError("--timeout-seconds must be positive")
        request = CreateRequest(
            issue_type=args.issue_type,
            domain=args.domain,
            short_title=title,
            body=body,
            repository=repository,
            parent_number=args.parent,
            requested_status=args.status,
            project_id=args.project_id,
        )
        report = create_and_verify(
            request,
            rules,
            GhClient(timeout_seconds=args.timeout_seconds),
            skill_file=skill_file,
        )
    except PartialSuccessError as error:
        print(json.dumps(error.report, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    except IssueCreateError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
