# Local Worktree Branch Cleanup

Historical local worktrees may still use old coding-agent branch prefixes. Treat them as local state first, not as repo state to rewrite blindly.

## Confirm

```bash
git worktree list
gh pr list --state open --json number,headRefName,title,url
```

Use the PR list to distinguish active review branches from stale local scratch work.

## Decide

- If the branch has an open PR, replace it with a type-first branch such as `docs/local-worktree-branch-cleanup`, then close the old PR as superseded.
- If the worktree is detached, locked, dirty, or unrelated to the current ticket, leave it alone and report it as local follow-up.
- If the branch is stale and clean with no open PR, remove the worktree only after confirming it has no useful local state.

## Rename

For an active branch that is safe to keep:

```bash
git -C <worktree-path> status --short --branch
git -C <worktree-path> branch -m docs/<short-slug>
git -C <worktree-path> push -u origin docs/<short-slug>
```

Do not use coding-agent prefixes such as `codex/`, `claude/`, or `agent/` for replacement branches.

## Remove

For stale clean worktrees with no open PR:

```bash
git worktree remove <worktree-path>
git worktree prune
```

Do not force-remove a worktree unless the owner has explicitly accepted losing its local state.
