<!-- omit in toc -->
# Infrastructure & DevOps
Deployment automation & DevOps scripts

<!-- omit in toc -->
## Table of Contents
- [Repository Structure](#repository-structure)
  - [GitHub Workflows](#github-workflows)
    - [Repo Version Reporter (`repo-version-reporter.yml`):](#repo-version-reporter-repo-version-reporteryml)
    - [Labeler (`labeler.yml`):](#labeler-labeleryml)
    - [Stale Issues and PRs (`stale.yml`):](#stale-issues-and-prs-staleyml)
    - [Python Testing and Linting (`ci.yml`):](#python-testing-and-linting-ciyml)
    - [Python Semantic Release and Changelog Generation (`semantic-release.yml`):](#python-semantic-release-and-changelog-generation-semantic-releaseyml)

## Repository Structure
### GitHub Workflows
#### Repo Version Reporter (`repo-version-reporter.yml`):
- A GitHub Action that runs weekly to report the latest release versions of all Astro repositories to a specified Discord channel via a WebHook.
- Helps the team stay updated on the latest versions of each repository for maintenance and integration purposes.

#### Labeler (`labeler.yml`):
> Reusable workflow for all Astro repositories.
- Automatically applies labels to pull requests based on the files changed.
- Needs configuration in each repository via a `.github/labeler.yml` file to specify which labels correspond to which file patterns.

#### Stale Issues and PRs (`stale.yml`):
> Reusable workflow for all Astro repositories.
- Automatically marks issues and pull requests as stale after a period of inactivity.
- Helps maintainers manage and clean up inactive issues and PRs in the repositories.

#### Python Testing and Linting (`ci.yml`):
> Reusable workflow for all Astro repositories.
- Runs python tests and linting checks to ensure code quality and functionality.
- Is expected to be triggered on pull requests to the `main` and `develop` branches of each repository.

#### Python Semantic Release and Changelog Generation (`semantic-release.yml`):
> Reusable workflow for all Astro repositories.
- Automates the release process by generating changelogs and creating new releases based on commit messages of Python projects.
- Is expected to be triggered on pushes to the `main` branch and also to be manually triggered via workflow dispatch.
