# Package Control submission checklist

## Repository entry

Use a public GitHub repository with the package root at the repository root.

Suggested entry for the centralized Package Control repository:

```json
{
  "name": "MarkdownJiraConverter",
  "details": "https://github.com/crqcastro/markdown_to_jira",
  "releases": [
    {
      "sublime_text": ">=4107",
      "tags": true
    }
  ],
  "labels": ["markdown", "jira", "converter", "text manipulation"]
}
```

## Before opening the PR

- Push this code to a public GitHub repository
- Create a semantic version tag such as `1.0.0`
- Confirm there is no `package-metadata.json` in the repo
- Confirm the package root is the repo root
- Confirm the package name matches the repository/package folder name

## Submit

1. Fork `package_control_channel`
2. Add the JSON entry to the appropriate file under `repository/`
3. Run ChannelRepositoryTools tests
4. Open a pull request
