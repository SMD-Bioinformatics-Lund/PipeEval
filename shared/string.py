from typing import Pattern


def get_match_or_crash(
    regex_pattern: Pattern[str], line: str, error_message: str
) -> str:
    match = regex_pattern.search(line)
    if match is None:
        raise ValueError(error_message)
    match_string = match.group(1)
    return match_string
