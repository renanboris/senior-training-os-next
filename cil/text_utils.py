from __future__ import annotations

import difflib
import unicodedata


class TextNormalizer:
    """Normaliza strings para comparação semântica."""

    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""
        # NFKD decomposition primeiro (expande compatibilidade, ex: ℌ → H)
        result = unicodedata.normalize("NFKD", text)
        # Remove combining characters (acentos)
        result = "".join(c for c in result if not unicodedata.combining(c))
        # lowercase após remoção de acentos (garante idempotência)
        result = result.lower()
        # colapso de espaços múltiplos + strip
        result = " ".join(result.split())
        return result


class SimilarityMatcher:
    """Calcula similaridade entre strings normalizadas."""

    def __init__(self, algorithm: str = "sequence_matcher") -> None:
        self.algorithm = algorithm
        self._normalizer = TextNormalizer()

    def score(self, a: str, b: str) -> float:
        """Retorna float em [0.0, 1.0]. Strings idênticas → 1.0. Simétrico."""
        na = self._normalizer.normalize(a)
        nb = self._normalizer.normalize(b)
        if na == nb:
            return 1.0
        if not na or not nb:
            return 0.0
        # Garante simetria: usa a média das duas direções
        r1 = difflib.SequenceMatcher(None, na, nb).ratio()
        r2 = difflib.SequenceMatcher(None, nb, na).ratio()
        return round(float((r1 + r2) / 2), 6)
