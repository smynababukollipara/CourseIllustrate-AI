import re


_LEGACY_ICON_MARKER = re.compile(r"::icon\([^)]*\)\s*")


def normalize_mermaid_source(source: str) -> str:
    """Keep legacy icon-based mind maps concise and remove unsupported icon nodes."""
    source = source or ""
    had_legacy_icons = "::icon(" in source

    if not had_legacy_icons:
        return source
    if not source.lstrip().lower().startswith("mindmap"):
        return _LEGACY_ICON_MARKER.sub("", source)

    lines = []
    skipped_indent = None
    for line in source.splitlines():
        indent = len(line) - len(line.lstrip())
        label = line.strip()
        if skipped_indent is not None:
            if label and indent > skipped_indent:
                continue
            skipped_indent = None
        if label.casefold() == "core concept":
            skipped_indent = indent
            continue
        if _LEGACY_ICON_MARKER.search(line):
            continue
        lines.append(line)
    return "\n".join(lines)
