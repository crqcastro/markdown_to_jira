import re
import sublime
import sublime_plugin


SETTINGS_FILE = "MarkdownJiraConverter.sublime-settings"


def plugin_settings():
    return sublime.load_settings(SETTINGS_FILE)


def get_setting(name, default=None):
    return plugin_settings().get(name, default)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def indent_level_from_spaces(spaces_count: int, spaces_per_indent: int) -> int:
    spaces_per_indent = max(1, spaces_per_indent)
    return max(1, (spaces_count // spaces_per_indent) + 1)


def protect_segments(text: str, pattern: str, formatter, flags=re.MULTILINE | re.DOTALL):
    stash = []

    def replacer(match):
        token = f"@@PROTECTED_{len(stash)}@@"
        stash.append(formatter(match))
        return token

    text = re.sub(pattern, replacer, text, flags=flags)
    return text, stash


def restore_segments(text: str, stash):
    for i, value in enumerate(stash):
        text = text.replace(f"@@PROTECTED_{i}@@", value)
    return text


# =========================
# Markdown -> Jira
# =========================

def md_to_jira(text: str) -> str:
    text = normalize_newlines(text)

    spaces_per_indent = int(get_setting("spaces_per_indent", 2))
    convert_tables = bool(get_setting("convert_tables", True))
    convert_images = bool(get_setting("convert_images", True))
    convert_blockquotes = bool(get_setting("convert_blockquotes", True))
    preserve_code_language = bool(get_setting("preserve_code_language", True))
    blockquote_multiline = bool(get_setting("blockquote_multiline", True))

    protected = []

    def fenced_code_formatter(match):
        lang = (match.group(1) or "").strip()
        content = match.group(2).rstrip("\n")
        if preserve_code_language and lang:
            return f"{{code:{lang}}}\n{content}\n{{code}}"
        return f"{{code}}\n{content}\n{{code}}"

    text, code_blocks = protect_segments(
        text,
        r"```([A-Za-z0-9_+\-]*)[ \t]*\n(.*?)\n```",
        fenced_code_formatter,
    )
    protected.extend(code_blocks)

    def inline_code_formatter(match):
        return "{{" + match.group(1) + "}}"

    text, inline_codes = protect_segments(
        text,
        r"`([^`\n]+)`",
        inline_code_formatter,
        flags=re.MULTILINE,
    )
    protected.extend(inline_codes)

    if convert_images:
        text = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", r"!\1!", text)

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"[\1|\2]", text)

    for level in range(6, 0, -1):
        text = re.sub(rf"^{'#' * level}\s+(.*)$", rf"h{level}. \1", text, flags=re.MULTILINE)

    if convert_blockquotes:
        lines = text.split("\n")
        out = []
        quote_buffer = []

        def flush_quote():
            nonlocal quote_buffer
            if not quote_buffer:
                return
            if blockquote_multiline:
                out.append("{quote}")
                out.extend(quote_buffer)
                out.append("{quote}")
            else:
                for line in quote_buffer:
                    out.append("{quote}" + line + "{quote}")
            quote_buffer = []

        for line in lines:
            if re.match(r"^\s*>\s?", line):
                quote_buffer.append(re.sub(r"^\s*>\s?", "", line))
            else:
                flush_quote()
                out.append(line)
        flush_quote()
        text = "\n".join(out)

    if convert_tables:
        lines = text.split("\n")
        out = []
        i = 0

        def is_separator(line: str) -> bool:
            stripped = line.strip()
            return bool(re.match(r"^\|?[\s:\-]+(\|[\s:\-]+)+\|?$", stripped))

        while i < len(lines):
            if "|" in lines[i] and i + 1 < len(lines) and is_separator(lines[i + 1]):
                table_lines = [lines[i], lines[i + 1]]
                i += 2
                while i < len(lines) and lines[i].strip() and "|" in lines[i]:
                    table_lines.append(lines[i])
                    i += 1

                headers = [c.strip() for c in table_lines[0].strip().strip("|").split("|")]
                jira_rows = ["|| " + " || ".join(headers) + " ||"]
                for body_line in table_lines[2:]:
                    cells = [c.strip() for c in body_line.strip().strip("|").split("|")]
                    jira_rows.append("| " + " | ".join(cells) + " |")
                out.extend(jira_rows)
                continue

            out.append(lines[i])
            i += 1

        text = "\n".join(out)

    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"__(.+?)__", r"*\1*", text)
    text = re.sub(r"~~(.+?)~~", r"-\1-", text)
    text = re.sub(r"(?<!\*)\*(?!\s)([^*\n]+?)(?<!\s)\*(?!\*)", r"_\1_", text)

    def unordered_replacer(match):
        spaces = len(match.group(1).replace("\t", "    "))
        level = indent_level_from_spaces(spaces, spaces_per_indent)
        return f'{"*" * level} {match.group(3)}'

    text = re.sub(r"^(\s*)([-+*])\s+(.*)$", unordered_replacer, text, flags=re.MULTILINE)

    def ordered_replacer(match):
        spaces = len(match.group(1).replace("\t", "    "))
        level = indent_level_from_spaces(spaces, spaces_per_indent)
        return f'{"#" * level} {match.group(2)}'

    text = re.sub(r"^(\s*)\d+\.\s+(.*)$", ordered_replacer, text, flags=re.MULTILINE)

    return restore_segments(text, protected)


# =========================
# Jira -> Markdown
# =========================

def jira_to_md(text: str) -> str:
    text = normalize_newlines(text)

    protected = []

    def jira_code_formatter(match):
        lang = (match.group(1) or "").strip(":")
        content = match.group(2).rstrip("\n")
        if lang:
            return f"```{lang}\n{content}\n```"
        return f"```\n{content}\n```"

    text, code_blocks = protect_segments(
        text,
        r"\{code(?::([A-Za-z0-9_+\-]+))?\}\n?(.*?)\n?\{code\}",
        jira_code_formatter,
    )
    protected.extend(code_blocks)

    def jira_inline_formatter(match):
        return "`" + match.group(1) + "`"

    text, inline_codes = protect_segments(
        text,
        r"\{\{([^}\n]+)\}\}",
        jira_inline_formatter,
        flags=re.MULTILINE,
    )
    protected.extend(inline_codes)

    def quote_block_replacer(match):
        content = match.group(1).strip("\n")
        return "\n".join("> " + line if line.strip() else ">" for line in content.split("\n"))

    text = re.sub(r"\{quote\}\n?(.*?)\n?\{quote\}", quote_block_replacer, text, flags=re.DOTALL)

    for level in range(6, 0, -1):
        text = re.sub(rf"^h{level}\.\s+(.*)$", rf"{'#' * level} \1", text, flags=re.MULTILINE)

    lines = text.split("\n")
    out = []
    i = 0

    def is_jira_header(line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("||") and stripped.endswith("||")

    def is_jira_row(line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("|") and stripped.endswith("|") and not stripped.startswith("||")

    while i < len(lines):
        if is_jira_header(lines[i]):
            table_lines = [lines[i]]
            i += 1
            while i < len(lines) and is_jira_row(lines[i]):
                table_lines.append(lines[i])
                i += 1

            header_cells = [c.strip() for c in table_lines[0].strip().strip("|").split("||") if c.strip()]
            out.append("| " + " | ".join(header_cells) + " |")
            out.append("| " + " | ".join(["---"] * len(header_cells)) + " |")

            for row in table_lines[1:]:
                body_cells = [c.strip() for c in row.strip().strip("|").split("|")]
                out.append("| " + " | ".join(body_cells) + " |")
            continue

        out.append(lines[i])
        i += 1

    text = "\n".join(out)

    text = re.sub(r"!(https?://[^!\s]+)!", r"![](\1)", text)
    text = re.sub(r"\[([^|\]]+)\|([^\]]+)\]", r"[\1](\2)", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"**\1**", text)
    text = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"*\1*", text)
    text = re.sub(r"(?<!\w)-([^- \n][^-\n]*?)-(?!(\w))", r"~~\1~~", text)

    def unordered_to_md(match):
        level = len(match.group(1))
        indent = "  " * (level - 1)
        return f"{indent}- {match.group(2)}"

    text = re.sub(r"^(\*+)\s+(.*)$", unordered_to_md, text, flags=re.MULTILINE)

    def ordered_to_md(match):
        level = len(match.group(1))
        indent = "  " * (level - 1)
        return f"{indent}1. {match.group(2)}"

    text = re.sub(r"^(#+)\s+(.*)$", ordered_to_md, text, flags=re.MULTILINE)

    return restore_segments(text, protected)


# =========================
# Shared command helpers
# =========================

def get_target_regions_and_texts(view):
    selections = list(view.sel())
    non_empty = [s for s in selections if not s.empty()]
    if non_empty:
        return non_empty, [view.substr(s) for s in non_empty]

    whole = sublime.Region(0, view.size())
    return [whole], [view.substr(whole)]


def replace_regions(view, edit, regions, transformed_parts):
    for region, content in zip(reversed(regions), reversed(transformed_parts)):
        view.replace(edit, region, content)


class BaseConversionCommand(sublime_plugin.TextCommand):
    convert_function = None
    copy_only = False

    def run(self, edit):
        if self.convert_function is None:
            sublime.error_message("Nenhuma função de conversão configurada.")
            return

        regions, texts = get_target_regions_and_texts(self.view)
        converted = [self.convert_function(text) for text in texts]

        if self.copy_only:
            sublime.set_clipboard("\n\n".join(converted))
            sublime.status_message("Texto convertido e copiado para o clipboard")
            return

        replace_regions(self.view, edit, regions, converted)
        sublime.status_message("Conversão concluída")


class MarkdownToJiraCommand(BaseConversionCommand):
    convert_function = staticmethod(md_to_jira)


class MarkdownToJiraCopyCommand(BaseConversionCommand):
    convert_function = staticmethod(md_to_jira)
    copy_only = True


class JiraToMarkdownCommand(BaseConversionCommand):
    convert_function = staticmethod(jira_to_md)


class JiraToMarkdownCopyCommand(BaseConversionCommand):
    convert_function = staticmethod(jira_to_md)
    copy_only = True
