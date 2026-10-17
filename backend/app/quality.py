from dataclasses import dataclass, field

import cv2
import numpy as np

# Starting thresholds. Tune them with scripts/check_quality.py on your own photos.
DARK_WARN, DARK_BAD = 50, 25            # mean gray level (0-255), lower = darker
BRIGHT_WARN, BRIGHT_BAD = 215, 238      # mean gray level, higher = more washed out
CONTRAST_WARN, CONTRAST_BAD = 22, 9     # std-dev of gray levels, lower = flatter
SHARP_WARN, SHARP_BAD = 40, 10          # variance of the Laplacian, lower = blurrier
ANALYSIS_SIDE = 512                     # compare images at the same scale

SEVERITY_ORDER = {"ok": 0, "warn": 1, "bad": 2}

MESSAGES = {
    "en": {
        "too_dark": "The photo is too dark. Turn on a light or move somewhere brighter, then try again.",
        "too_bright": "The photo is too bright or washed out. Move away from direct light or glare, then try again.",
        "blurry": "The photo is blurry. Hold the phone steady, then try again.",
        "low_contrast": "The photo looks flat or empty. Move closer to what you want described, then try again.",
    },
    "fr": {
        "too_dark": "La photo est trop sombre. Allumez une lumi\u00e8re ou allez dans un endroit plus clair, puis r\u00e9essayez.",
        "too_bright": "La photo est trop claire ou \u00e9blouie. \u00c9loignez-vous de la lumi\u00e8re directe ou du reflet, puis r\u00e9essayez.",
        "blurry": "La photo est floue. Tenez le t\u00e9l\u00e9phone bien stable, puis r\u00e9essayez.",
        "low_contrast": "La photo semble plate ou vide. Rapprochez-vous de ce que vous voulez d\u00e9crire, puis r\u00e9essayez.",
    },
    "ar": {
        "too_dark": "\u0627\u0644\u0635\u0648\u0631\u0629 \u0645\u0638\u0644\u0645\u0629 \u062c\u062f\u0627. \u0634\u063a\u0644 \u0627\u0644\u0625\u0636\u0627\u0621\u0629 \u0623\u0648 \u0627\u0646\u062a\u0642\u0644 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646 \u0623\u0643\u062b\u0631 \u0625\u0636\u0627\u0621\u0629\u060c \u062b\u0645 \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.",
        "too_bright": "\u0627\u0644\u0635\u0648\u0631\u0629 \u0633\u0627\u0637\u0639\u0629 \u062c\u062f\u0627. \u0627\u0628\u062a\u0639\u062f \u0639\u0646 \u0627\u0644\u0636\u0648\u0621 \u0627\u0644\u0645\u0628\u0627\u0634\u0631 \u0623\u0648 \u0627\u0644\u0627\u0646\u0639\u0643\u0627\u0633\u060c \u062b\u0645 \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.",
        "blurry": "\u0627\u0644\u0635\u0648\u0631\u0629 \u063a\u064a\u0631 \u0648\u0627\u0636\u062d\u0629. \u062b\u0628\u062a \u0627\u0644\u0647\u0627\u062a\u0641 \u062c\u064a\u062f\u0627\u060c \u062b\u0645 \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.",
        "low_contrast": "\u0627\u0644\u0635\u0648\u0631\u0629 \u062a\u0628\u062f\u0648 \u0641\u0627\u0631\u063a\u0629 \u0623\u0648 \u0628\u0627\u0647\u062a\u0629. \u0627\u0642\u062a\u0631\u0628 \u0645\u0645\u0627 \u062a\u0631\u064a\u062f \u0648\u0635\u0641\u0647\u060c \u062b\u0645 \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.",
    },
}


@dataclass
class QualityReport:
    metrics: dict
    issues: list = field(default_factory=list)  # [{"code": "...", "severity": "warn|bad"}]

    @property
    def severity(self) -> str:
        worst = "ok"
        for issue in self.issues:
            if SEVERITY_ORDER[issue["severity"]] > SEVERITY_ORDER[worst]:
                worst = issue["severity"]
        return worst

    def to_dict(self, lang: str = "en") -> dict:
        return {
            "ok": self.severity == "ok",
            "severity": self.severity,
            "issues": [issue["code"] for issue in self.issues],
            "advice": advice(self, lang),
            "metrics": self.metrics,
        }


def advice(report: QualityReport, lang: str = "en") -> str:
    """Spoken-friendly advice for the most serious problem ('' if the photo is fine)."""
    if not report.issues:
        return ""
    worst = max(report.issues, key=lambda i: SEVERITY_ORDER[i["severity"]])
    table = MESSAGES.get(lang, MESSAGES["en"])
    return table[worst["code"]]


def analyze_quality(image_bytes: bytes) -> QualityReport:
    """Check brightness, contrast and sharpness of an encoded image (JPEG/PNG bytes)."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    gray = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError("Could not decode the image for the quality check.")

    h, w = gray.shape
    scale = ANALYSIS_SIDE / max(h, w)
    if scale < 1:
        gray = cv2.resize(gray, (max(1, round(w * scale)), max(1, round(h * scale))), interpolation=cv2.INTER_AREA)

    mean = float(gray.mean())
    std = float(gray.std())
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    metrics = {"brightness": round(mean, 1), "contrast": round(std, 1), "sharpness": round(sharpness, 1)}

    issues = []
    if mean < DARK_WARN:
        issues.append({"code": "too_dark", "severity": "bad" if mean < DARK_BAD else "warn"})
    elif mean > BRIGHT_WARN:
        issues.append({"code": "too_bright", "severity": "bad" if mean > BRIGHT_BAD else "warn"})
    elif std < CONTRAST_WARN:
        issues.append({"code": "low_contrast", "severity": "bad" if std < CONTRAST_BAD else "warn"})
    elif sharpness < SHARP_WARN:
        issues.append({"code": "blurry", "severity": "bad" if sharpness < SHARP_BAD else "warn"})
    return QualityReport(metrics=metrics, issues=issues)
