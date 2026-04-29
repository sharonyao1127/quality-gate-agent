# GitHub PR Comment Workflow

Future workflow:

1. Developer opens a pull request.
2. GitHub Action collects git diff and API change summary.
3. Quality Gate Agent analyzes risk.
4. The agent generates `outputs/pr_comment.md`.
5. CI posts the comment to the PR.
6. High-risk changes require manual QA review before merge.
