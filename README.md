# MarkdownJiraConverter

A Sublime Text package to convert between Markdown and Jira text formatting.

## Features

- Markdown -> Jira
- Jira -> Markdown
- Works on the current selection or the whole file
- Copy converted output to the clipboard
- Supports headings, lists, links, images, code blocks, inline code, blockquotes and basic tables

## Commands

- `Markdown/Jira: Convert Markdown to Jira`
- `Markdown/Jira: Copy Markdown as Jira`
- `Markdown/Jira: Convert Jira to Markdown`
- `Markdown/Jira: Copy Jira as Markdown`

## Installation

### Package Control

1. Open the Command Palette
2. Run `Package Control: Install Package`
3. Search for `MarkdownJiraConverter`

### Manual

Clone or copy this repository into your Sublime Text `Packages` directory.

## Settings

Create `Preferences > Package Settings > MarkdownJiraConverter > Settings – User` with:

```json
{
  "spaces_per_indent": 2,
  "convert_tables": true,
  "convert_images": true,
  "convert_blockquotes": true,
  "blockquote_multiline": true,
  "preserve_code_language": true
}
```

## Releases

Package Control expects semantic version tags such as `1.0.0`, `1.0.1`, `1.1.0`.

## Notes

Do not commit `package-metadata.json` to this repository. Package Control generates it on install.
