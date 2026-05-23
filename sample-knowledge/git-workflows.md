# Git Workflows and Team Collaboration

This guide covers branching strategies, pull request practices, and CI/CD integration for teams using Git.

## Git Flow

Git Flow uses a rigid set of branches suited to projects with scheduled releases:

- **main** - production-ready code only. Never commit here directly.
- **develop** - integration branch for completed features.
- **feature/*** - branched from `develop`, merged back when done.
- **release/*** - branched from `develop` when preparing a release; only bug fixes go here.
- **hotfix/*** - branched from `main` for urgent production fixes; merged to both `main` and `develop`.

```
main ←────────────────────── hotfix/critical-bug
  ↑                                ↑
develop ←── feature/login ←── release/1.2
```

Use Git Flow when: multiple versions in production, scheduled release cadence, large teams needing strict discipline.

## Trunk-Based Development (TBD)

Everyone commits small changes directly to `main` (or a single trunk branch) multiple times per day.

Rules:
- Branches live at most 1–2 days before merging.
- Feature flags hide incomplete work in production.
- A comprehensive automated test suite is non-negotiable.
- No long-lived feature branches.

Use TBD when: continuous deployment, small–medium teams, high test coverage, fast feedback cycles.

## GitHub Flow

A simpler alternative to Git Flow:
1. Branch off `main` with a descriptive name (`feature/add-login`, `fix/broken-nav`).
2. Commit early and often on your branch.
3. Open a Pull Request (PR) when ready for review - even if not finished ("Draft PR").
4. Reviewers comment; author addresses feedback with new commits.
5. CI must pass before merge.
6. Merge to `main` → deploy immediately.

```bash
git checkout -b feature/user-profile
# ... work ...
git push origin feature/user-profile
# open PR on GitHub
```

## Writing Good Commit Messages

Follow the Conventional Commits convention:

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(auth): add OAuth2 login with Google
fix(api): handle null response from payments endpoint
docs(readme): add Docker setup instructions
refactor(db): extract connection pooling to separate module
```

Rules:
- Subject line ≤ 72 characters.
- Use the imperative mood: "Add feature" not "Added feature".
- Reference issue numbers in the footer: `Closes #142`.

## Pull Request Best Practices

**Author responsibilities:**
- Keep PRs small - under 400 lines of change is a good guideline.
- Describe *why* the change was made, not just *what* changed.
- Self-review your diff before requesting review.
- Respond to feedback promptly; don't let PRs go stale.

**Reviewer responsibilities:**
- Review within 24 hours on working days.
- Be specific: reference line numbers, suggest concrete alternatives.
- Approve explicitly when satisfied; don't silently merge.
- Check: correctness, tests, security implications, backward compatibility.

## Resolving Conflicts on a Team

When two developers modify the same file:

```bash
git fetch origin
git merge origin/main          # or: git rebase origin/main
# resolve conflicts in editor
git add resolved-file.py
git merge --continue           # or: git rebase --continue
```

Best practice: pull from `main` daily to keep your branch up to date and reduce conflict surface.

## Protecting the Main Branch

Configure branch protection rules in GitHub/GitLab:
- Require at least 1 approving review.
- Require CI checks to pass.
- Require branches to be up-to-date before merging.
- Restrict who can push directly.

These rules prevent accidental broken builds on `main`.
