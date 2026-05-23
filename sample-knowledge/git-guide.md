# Git Version Control - Practical Guide

Git is a distributed version control system. Every developer has a full copy of the repository history locally.

## Core Concepts

- **Repository (repo)**: The folder tracked by Git, including the full history.
- **Working tree**: The files you currently see and edit.
- **Staging area (index)**: Where you prepare changes before committing.
- **Commit**: A snapshot of the staged changes, stored permanently in history.
- **Branch**: A lightweight pointer to a commit - lets you work in parallel without affecting `main`.
- **Remote**: A copy of the repo hosted elsewhere (e.g., GitHub, GitLab).

## Essential Commands

### Initialise and clone

```bash
git init                         # start tracking a new folder
git clone https://repo-url.git   # copy an existing remote repo locally
```

### Daily workflow

```bash
git status                      # see what has changed
git diff                        # show unstaged changes line by line
git add file.py                 # stage a specific file
git add .                       # stage all changes
git commit -m "short message"   # create a commit
git push origin main            # upload commits to the remote
git pull                        # fetch + merge latest from remote
```

### Branching

```bash
git branch feature/login        # create a branch
git checkout feature/login      # switch to it
git checkout -b feature/login   # create and switch in one step
git merge feature/login         # merge branch into current branch
git branch -d feature/login     # delete merged branch
```

### Undoing changes

```bash
git restore file.py             # discard unstaged changes to a file
git restore --staged file.py    # unstage a file (keep changes in working tree)
git revert HEAD                 # create a new commit that undoes the last one
git reset --soft HEAD~1         # move HEAD back one commit, keep changes staged
```

## Branching Strategies

### Git Flow
Uses `main`, `develop`, `feature/*`, `release/*`, and `hotfix/*` branches. Good for projects with scheduled releases.

### Trunk-Based Development
Everyone merges small changes directly into `main` frequently. Feature flags hide incomplete work. Preferred for CI/CD pipelines.

### GitHub Flow
Short-lived feature branches off `main`, opened as Pull Requests, reviewed, then merged. Simple and widely used.

## Merge vs Rebase

| | Merge | Rebase |
|---|---|---|
| History | Preserves full branch history | Rewrites commits onto target branch - cleaner linear history |
| Safety | Always safe | Never rebase shared/public branches |
| Use case | Feature integration | Cleaning up local commits before PR |

## Conflict Resolution

When Git cannot automatically merge changes, it inserts conflict markers:

```
<<<<<<< HEAD
your version of the code
=======
their version of the code
>>>>>>> feature/login
```

Edit the file to keep the correct version, remove the markers, then `git add` and `git commit`.

## .gitignore

List patterns of files Git should not track:

```
# Python
__pycache__/
*.pyc
.venv/

# Secrets
.env
*.key
```
