import re

try:
    from underthesea import sent_tokenize as _vn_sent_tokenize
except Exception:  # underthesea không có hoặc lỗi: dùng cách tách bằng regex
    _vn_sent_tokenize = None

_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+|\n+")
_NUMBER_RE = re.compile(r"\d")
_UNIT_RE = re.compile(r"%|\b(?:phần trăm|tỷ|triệu|nghìn|đồng|usd|km|kg)\b", re.I)
_DATE_RE = re.compile(r"\b(?:ngày|tháng|năm|quý)\s*\d", re.I)


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    parts: list[str] = []
    if _vn_sent_tokenize is not None:
        try:
            parts = list(_vn_sent_tokenize(text))
        except Exception:
            parts = []
    if not parts:
        parts = _SPLIT_RE.split(text)
    return [p.strip() for p in parts if p and p.strip()]


def _has_proper_noun(sentence: str) -> bool:
    # Từ viết hoa không đứng đầu câu thường là tên riêng (người, cơ quan, địa danh)
    return any(w[:1].isupper() for w in sentence.split()[1:])


def _score(sentence: str) -> int:
    """Chấm điểm 'tính khẳng định có thể kiểm chứng' của một câu."""
    n = len(sentence.split())
    if n < 6 or sentence.endswith("?"):
        return -1
    score = 0
    if _NUMBER_RE.search(sentence):
        score += 2
    if _UNIT_RE.search(sentence):
        score += 1
    if _DATE_RE.search(sentence):
        score += 1
    if _has_proper_noun(sentence):
        score += 1
    if 8 <= n <= 45:
        score += 1
    return score


def extract_claims(text: str, max_claims: int = 3) -> list[str]:
    sentences = split_sentences(text)
    if not sentences:
        return []
    if len(sentences) == 1:
        return sentences

    scored = [(i, _score(s), s) for i, s in enumerate(sentences)]
    candidates = [x for x in scored if x[1] >= 1]
    if not candidates:
        candidates = [x for x in scored if x[1] >= 0] or scored[:1]

    top = sorted(candidates, key=lambda x: (-x[1], x[0]))[:max_claims]
    top.sort(key=lambda x: x[0])  # giữ thứ tự xuất hiện trong văn bản
    return [s for _, _, s in top]
