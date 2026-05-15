import re

def join_pages(pages: list[str]) -> str:
    """
    Joins multiple pages of text with a single newline.
    """
    return "\n".join(pages)

def get_header_fingerprint(page_text: str) -> str:
    """
    Extracts the first 3 non-empty lines of a page to use as a header fingerprint.
    """
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    return "\n".join(lines[:3])

def strip_repeated_headers(text: str, header_fingerprint: str) -> str:
    """
    Detects and removes any occurrences of the header_fingerprint from the text.
    """
    if not header_fingerprint:
        return text
    
    # We will just replace the exact literal fingerprint string if it occurs in the text,
    # but considering it might have been split by different numbers of newlines, a regex matching ignoring whitespace might be better.
    # To keep it robust, we'll construct a regex from the fingerprint lines.
    
    lines = header_fingerprint.splitlines()
    if not lines:
        return text
        
    escaped_lines = [re.escape(line) for line in lines]
    # Allow any amount of whitespace (including newlines) between the header lines
    pattern = r"\s*".join(escaped_lines)
    
    # Replace all matches with empty string.
    # Note: We might inadvertently remove the first occurrence (which is the actual header on page 1).
    # To avoid this, we can find all matches and only keep the first, or we just remove all and prepend one?
    # Usually we want the first occurrence to remain if it's the start of the document.
    # Let's replace only occurrences that happen after the very start, or simply replace all and then prepend the header if we want to keep it?
    # The prompt says "Remove subsequent occurrences of these lines (from page 2+)".
    # If the text is already joined, the first occurrence will be at index 0 or close to it.
    
    # Better approach: find all occurrences, keep the first one intact.
    regex = re.compile(pattern)
    
    matches = list(regex.finditer(text))
    if not matches:
        return text
        
    # Keep the first match (assumed to be page 1 header)
    first_match = matches[0]
    
    # Rebuild the string without subsequent matches
    result = []
    last_end = first_match.end()
    
    # Append the part up to the end of the first match
    result.append(text[:last_end])
    
    for match in matches[1:]:
        result.append(text[last_end:match.start()])
        last_end = match.end()
        
    result.append(text[last_end:])
    
    return "".join(result)

def normalise_whitespace(text: str) -> str:
    """
    Collapses runs of 3+ consecutive newlines to exactly 2 newlines.
    Does not strip single newlines.
    """
    return re.sub(r"\n{3,}", "\n\n", text)


def strip_page_artifacts(text: str) -> str:
    """
    HP-07: Remove page number artifacts (e.g. '2 / 3') and orphan page-break lines
  before Epicriza LLM submission.
    """
    if not text:
        return text
    # Page numbers like "2 / 3" or "2/3"
    text = re.sub(r"(?m)^\s*\d+\s*/\s*\d+\s*$", "", text)
    # Standalone page indicators
    text = re.sub(r"(?m)^\s*-\s*\d+\s*-\s*$", "", text)
    return normalise_whitespace(text)
