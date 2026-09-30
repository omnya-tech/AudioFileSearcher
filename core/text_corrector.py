import re

# الحروف التي تلتصق ببداية الكلمة العربية (و، ف، ب، ك، ل، ال وتركيباتها)
ARABIC_PREFIXES = ["وبال", "وكال", "فبال", "وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ك", "ل"]
# التشكيل والتطويل
ARABIC_MARKS = "ً-ْٰـ"
# أقل طول للكلمة حتى نسمح بالتقاط الحروف الملتصقة بها (لتجنب تصحيح أجزاء من كلمات أخرى)
MIN_LEN_FOR_PREFIXES = 3

_MARKS_RE = re.compile(f"[{ARABIC_MARKS}]")


def normalize_arabic(text):
    """توحيد أشكال الحروف المتشابهة وحذف التشكيل (يُستخدم في مستوى التصحيح العميق فقط)"""
    text = _MARKS_RE.sub("", text)
    text = re.sub("[أإآٱ]", "ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه")
    return text.lower()


def _loose_pattern(word):
    """نمط يطابق الكلمة مع تجاهل التشكيل واختلاف أشكال الألف والياء والتاء المربوطة"""
    classes = {"ا": "[اأإآٱ]", "أ": "[اأإآٱ]", "إ": "[اأإآٱ]", "آ": "[اأإآٱ]", "ٱ": "[اأإآٱ]",
               "ي": "[يى]", "ى": "[يى]", "ة": "[ةه]", "ه": "[ةه]"}
    parts = [classes.get(ch, re.escape(ch)) for ch in _MARKS_RE.sub("", word)]
    return f"[{ARABIC_MARKS}]*".join(parts) + f"[{ARABIC_MARKS}]*"


class TextCorrector:
    """
    مستويات التصحيح:
      light      : يستبدل الكلمة فقط لو جاءت منفصلة تماماً كما هي.
      medium     : نفس السابق + يلتقط الكلمة حتى لو التصق بها (ال، و، ب، ...) ويحافظ عليها.
      aggressive : نفس السابق + يتجاهل التشكيل واختلاف (أ/إ/آ/ا) و(ى/ي) و(ة/ه) وحالة الحروف اللاتينية.
    الاستبدال يتم في مرور واحد، فلا يمكن أن يتم تصحيح كلمة تم تصحيحها بالفعل مرة أخرى.
    """

    def __init__(self, dictionary=None):
        self.dictionary = {k.strip(): v.strip() for k, v in (dictionary or {}).items()
                           if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip()}
        self._cache = {}

    def _build(self, level):
        if level in self._cache:
            return self._cache[level]

        # ترتيب الكلمات من الأطول للأقصر حتى تُفضَّل العبارات الأطول عند التداخل
        words = sorted(self.dictionary.keys(), key=len, reverse=True)
        aggressive = level == "aggressive"
        use_prefixes = level in ("medium", "aggressive")

        long_alts, short_alts = [], []
        for w in words:
            alt = _loose_pattern(w) if aggressive else re.escape(w)
            (long_alts if len(w) >= MIN_LEN_FOR_PREFIXES else short_alts).append(alt)

        branches = []
        if long_alts:
            prefix = "(?P<p1>" + "|".join(ARABIC_PREFIXES) + ")?" if use_prefixes else "(?P<p1>)"
            branches.append(prefix + "(?P<w1>" + "|".join(long_alts) + ")")
        if short_alts:
            branches.append("(?P<p2>)(?P<w2>" + "|".join(short_alts) + ")")

        if not branches:
            self._cache[level] = None
            return None

        pattern = r"(?<!\w)(?:" + "|".join(branches) + r")(?!\w)"
        flags = re.IGNORECASE if aggressive else 0
        lookup = {normalize_arabic(k): v for k, v in self.dictionary.items()} if aggressive else dict(self.dictionary)
        compiled = (re.compile(pattern, flags), lookup, aggressive)
        self._cache[level] = compiled
        return compiled

    def correct(self, text, level="medium"):
        if not text or not self.dictionary:
            return text

        built = self._build(level if level in ("light", "medium", "aggressive") else "medium")
        if not built:
            return text
        regex, lookup, aggressive = built

        def replace(match):
            # بعض المجموعات قد لا تكون موجودة في النمط (لو كل الكلمات قصيرة أو كلها طويلة)
            groups = match.groupdict()
            prefix = groups.get("p1") or groups.get("p2") or ""
            word = groups.get("w1") if groups.get("w1") is not None else groups.get("w2")
            key = normalize_arabic(word) if aggressive else word
            right = lookup.get(key)
            if right is None:
                return match.group(0)
            # "ال" لا تتكرر لو كان البديل الصحيح يبدأ بها أصلاً
            if prefix.endswith("ال") and right.startswith("ال"):
                prefix = prefix[:-2]
            return prefix + right

        return regex.sub(replace, text)

    def get_hotwords(self):
        """الكلمات الصحيحة تُمرَّر للنموذج كتلميح لرفع احتمال كتابتها بشكل صحيح"""
        unique = list(dict.fromkeys(self.dictionary.values()))
        return ", ".join(unique) if unique else None
