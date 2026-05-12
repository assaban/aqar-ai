# Contributing to Aqar.ai

## Development Workflow

### 1. Branch Setup (One-Time)

```bash
# Clone the repo
git clone git@github.com:assaban/aqar-ai.git
cd aqar-ai

# Create and push the dev branch (if it doesn't exist)
git checkout -b dev
git push -u origin dev

# Set up the environment
cp .env.example .env
make dev
make migrate
make health
```

### 2. Starting a New Feature

Every feature maps to a user story (US-XXX) and one or more issues (AQAR-XXX).

```bash
# Always start from the latest dev
git checkout dev
git pull origin dev

# Create the feature branch
git checkout -b feature/AQAR-XXX-short-description

# Create the feature documentation
cp docs/features/TEMPLATE.md docs/features/AQAR-XXX-short-description.md
# Edit the feature doc with your analysis & design
```

### 3. Working on the Feature

```bash
# Make changes, test locally
make test-unit

# Commit with conventional commits
git add .
git commit -m "feat(pipeline): implement YouTube video discovery

- Add discover_videos Celery task
- Create YouTube channel config
- Add yt-dlp metadata extraction wrapper

Implements: AQAR-017, AQAR-018, AQAR-019"

# Push to remote
git push origin feature/AQAR-XXX-short-description
```

### 4. Creating a Pull Request

1. Go to [github.com/assaban/aqar-ai](https://github.com/assaban/aqar-ai)
2. Create PR: `feature/AQAR-XXX-short-description` → `dev`
3. PR title: `feat(scope): Short description [AQAR-XXX]`
4. PR description should reference:
   - User story ID (US-XXX)
   - Issues closed (Closes #XX, Closes #YY)
   - Link to feature doc
   - Test results

### 5. Merging to Dev

After CI passes and review is complete:

```bash
# Merge PR on GitHub (squash merge preferred)
# Then update your local dev
git checkout dev
git pull origin dev
```

### 6. Releasing to Main (End of Sprint)

At the end of a sprint, when all features for that sprint are merged into `dev`:

```bash
# Create a PR: dev → main
# Title: "Release: Sprint X: [Sprint Name]"
# Include summary of all features shipped

# After merge, tag the release
git checkout main
git pull origin main
git tag -a vX.Y.Z -m "Sprint X: [Sprint Name]"
git push origin vX.Y.Z
```

### 7. Hotfixes

For urgent fixes to production:

```bash
git checkout main
git pull origin main
git checkout -b hotfix/fix-description

# Make the fix, commit, push
git commit -m "fix(api): correct database connection timeout"
git push origin hotfix/fix-description

# Create TWO PRs:
# 1. hotfix/fix-description → main
# 2. hotfix/fix-description → dev (to keep dev in sync)
```

## Commit Convention

| Prefix | Use Case | Example |
|--------|----------|---------|
| `feat` | New feature | `feat(pipeline): add audio extraction` |
| `fix` | Bug fix | `fix(api): correct pagination offset` |
| `docs` | Documentation | `docs: update contributing guide` |
| `test` | Tests | `test(pipeline): add ingestion tests` |
| `refactor` | Refactoring | `refactor(db): simplify model relationships` |
| `chore` | Maintenance | `chore: upgrade dependencies` |
| `ci` | CI/CD changes | `ci: add Docker build caching` |

## Code Quality Checklist

Before pushing, ensure:

- [ ] `make test-unit` passes
- [ ] `make lint` passes
- [ ] Feature doc created/updated in `docs/features/`
- [ ] New code has docstrings
- [ ] No secrets or API keys committed
