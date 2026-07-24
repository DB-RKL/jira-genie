# Contributing

Thank you for your interest in contributing to Jira Analytics.

## Contributor License Agreement

By submitting a contribution to this repository, you certify that:

1. **You have the right to submit the contribution.** You created the code/content yourself, or you have the right to submit it under the project's license.

2. **You grant us a license to use your contribution.** You agree that your contribution will be licensed under the same terms as the rest of this project (Apache License 2.0).

3. **You are not submitting confidential or proprietary information.** Your contribution does not include anything you do not have permission to share publicly.

## How to Contribute

1. Fork the repository and create a feature branch.
2. Make your changes with clear commit messages.
3. Run `./scripts/sync_config.sh` and `databricks bundle validate -t dev` if you changed bundle resources.
4. Open a pull request describing the change and test plan.

## Code Style

- Match existing conventions in the file you are editing.
- Keep changes focused — one logical change per pull request.
- Update `docs/` and `CHANGELOG.md` for user-facing changes.
