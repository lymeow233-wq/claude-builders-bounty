# Submission Draft

Status: not submitted.

## Project

Claude PR Reviewer Agent for Claude Builders Bounty issue #4.

## What It Delivers

- Dependency-free Python CLI installable as `claude-review`.
- Reviews either a GitHub PR URL or a local unified diff.
- Accepts both full PR URLs and `owner/repo#123` shorthand.
- Emits the required Markdown sections: Summary, Identified Risks, Improvement Suggestions, Confidence Score.
- Produces deterministic structured findings with rule code, severity, path, line, and short evidence when available.
- Tracks changed functions/classes/exports/constants against downstream non-test callers in the PR diff.
- Supports `--repo-root` to scan a local checkout for non-test references outside the PR diff.
- Flags touched tests that do not reference changed existing-file symbols with `CHANGED_SYMBOL_WITHOUT_RELEVANT_TEST` while avoiding one finding per helper in all-new packages.
- Runtime-risk rules skip tests, documentation, fixtures, examples, and saved sample reports by default so intentionally dangerous fixtures do not masquerade as production risks.
- Supports JSON output for automation via `--format json`.
- Supports SARIF 2.1.0 output via `--format sarif`.
- Supports `.claude-review.yml`, `.claude-review.yaml`, or `.claude-review.json` configuration for disabled rules, ignored paths, and severity overrides.
- Supports optional external LLM review generation via `--llm-command`, with a stable JSON prompt contract.
- Supports `--prompt-only` for prompt inspection or manual LLM handoff.
- Can post or update a GitHub PR comment through `gh` using `--post-comment` or `--update-comment`.
- Emits GitHub Actions file/line warning annotations for located findings with `--github-annotations`.
- Appends Markdown output to a GitHub Actions job summary with `--step-summary`.
- Supports `--allow-comment-failure` so fork PR read-only token failures still leave annotations and summary output.
- Includes a copyable GitHub Actions workflow example.
- Includes an optional SARIF upload workflow example at `agents/pr-reviewer/github-action-sarif.yml`.
- Includes a reusable local composite action at `agents/pr-reviewer/action.yml`.
- Includes `.claude-review.example.yml` as a project config starter.

## Hardening Notes

- Empty diffs are rejected before output.
- `--max-diff-chars` defaults to `500000` and has a lower bound to avoid unusable parser context.
- PR URL parsing rejects issue URLs and malformed GitHub URLs.
- Comment posting validates Markdown mode and PR input before printing review output.
- Existing generated PR comments are updated by hidden marker instead of duplicating comments.
- PR comment failures can be non-blocking when annotations/summary are already emitted.
- Diff parser preserves paths with spaces and tracks added-line numbers from hunk headers.
- Dependency-impact analysis ignores import-only lines when a real usage line is available.
- Repository scanning is bounded by file count, file size, extension allowlist, and common generated/vendor directory exclusions.
- Credential-like evidence is masked in rendered output.
- External LLM commands run without `shell=True`, receive prompt text on stdin, and must return parseable JSON.
- YAML config support is intentionally a dependency-free subset; complex configs can use JSON.

## Competitor Scan

Reviewed public issue #4 submissions and PR descriptions on 2026-05-13, including PR #806, #950, #985, #987, #1046, #1097, #1149, and #965.

Absorbed:

- `owner/repo#123` PR shorthand from lightweight CLI submissions.
- Local composite `action.yml` pattern from reusable-action submissions.
- Fork-safe GitHub Actions visibility via annotations and step summary, informed by action-oriented submissions and GitHub token permission constraints.
- Test relevance checks, added to go beyond submissions that only detect whether any test file changed.

Not copied:

- Full multi-agent orchestration from #806, because it adds prompt surface area and operational complexity; this implementation keeps a deterministic analyzer plus optional external LLM backend.
- Heavy provider-specific SDK defaults from model-backed submissions, because the bounty acceptance criteria benefits from no-key local verification.

## Verification

Run from the repository root:

```bash
python -m unittest discover -s agents/pr-reviewer/tests
python -m py_compile agents/pr-reviewer/claude-review.py agents/pr-reviewer/claude_review/cli.py agents/pr-reviewer/tests/test_claude_review.py
python agents/pr-reviewer/claude-review.py --diff-file agents/pr-reviewer/tests/fixtures/security.diff
python agents/pr-reviewer/claude-review.py --diff-file agents/pr-reviewer/tests/fixtures/security.diff --format json
python agents/pr-reviewer/claude-review.py --diff-file agents/pr-reviewer/tests/fixtures/dependency_impact.diff --format sarif
python agents/pr-reviewer/claude-review.py --diff-file agents/pr-reviewer/tests/fixtures/dependency_impact.diff
python agents/pr-reviewer/claude-review.py --diff-file agents/pr-reviewer/tests/fixtures/dependency_impact.diff --github-annotations --step-summary /tmp/claude-review-summary.md
python agents/pr-reviewer/claude-review.py --diff-file agents/pr-reviewer/tests/fixtures/security.diff --prompt-only
python agents/pr-reviewer/claude-review.py --pr https://github.com/octocat/Hello-World/pull/1 --no-gh --format json
python agents/pr-reviewer/claude-review.py --pr octocat/Hello-World#1 --no-gh --format json
```

Latest local verification on 2026-05-13:

```text
python -m unittest discover -s agents/pr-reviewer/tests
Ran 28 tests - OK

python -m py_compile agents/pr-reviewer/claude-review.py agents/pr-reviewer/claude_review/cli.py agents/pr-reviewer/tests/test_claude_review.py
passed
```

Real GitHub Actions workflow smoke on 2026-05-13:

```text
Temporary fork-only PR: https://github.com/lymeow233-wq/claude-builders-bounty/pull/1
Run: https://github.com/lymeow233-wq/claude-builders-bounty/actions/runs/25775489805
Result: success
Verified: composite action installed the package, ran `claude-review --pr ... --repo-root . --github-annotations --step-summary --update-comment`, and updated the existing bot comment by marker.
```

## Sample Outputs

Stored in `agents/pr-reviewer/samples/`:

- `fixture-security-review.md`
- `fixture-dependency-impact-review.md`
- `fixture-safe-review.md`
- `claude-builders-bounty-950.md`
- `claude-builders-bounty-1097.md`
- `psf-requests-7310.md`
- `pallets-flask-6018.md`
- `vercel-nextjs-93794.md`

## Known Limits

- The deterministic analyzer is a first-pass reviewer, not a full semantic code execution engine.
- Line-level findings are available for added lines in unified diffs; file-level findings are used when the risk is inferred from path coverage.
- Dependency tracking is symbol/reference based, not a full language-server call graph. It is meant to surface likely downstream risk and test gaps.
- GitHub annotations are warnings by design; they make findings visible without turning the review job into a merge blocker.
- SARIF upload depends on repository/code-scanning permissions; the CLI still emits SARIF locally without those permissions.
- Public PR samples can drift if upstream branches change before merge.
