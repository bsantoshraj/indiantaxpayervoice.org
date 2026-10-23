"""Generate a LimeSurvey tab-separated survey structure (.txt) from questionnaire-v1.json.

The questionnaire JSON is the single source of truth: the aggregator validates
exports against it and this script produces the importable survey, so codes
cannot drift apart. Usage:

    python3 survey/build_structure.py survey/questionnaire-v1.json > survey.txt
"""

from __future__ import annotations

import csv
import io
import json
import sys

LANG = "en"
COLUMNS = [
    "class", "type/scale", "name", "relevance", "text", "help", "language", "validation",
    "em_validation_q", "em_validation_sq", "mandatory", "other", "default", "same_default",
    "max_answers", "maximum_chars", "em_validation_q_tip",
]
QTYPES = {"list": "L", "multi": "M", "text": "T"}

# Survey-wide settings. Anonymised (no link to participant tokens), no IP or
# referrer capture, no save-and-resume (which would ask for an email address).
SURVEY_SETTINGS = {
    "language": LANG,
    "anonymized": "Y",
    "datestamp": "Y",  # needed for weekly trends; never published below week level
    "ipaddr": "N",
    "ipanonymize": "Y",
    "refurl": "N",
    "savetimings": "N",
    "allowsave": "N",
    "allowprev": "Y",
    "format": "G",
    "showprogress": "Y",
    "showwelcome": "Y",
    "questionindex": "0",
    "showxquestions": "N",
    "shownoanswer": "Y",
    "printanswers": "N",
    "publicstatistics": "N",
    "publicgraphs": "N",
    "usecookie": "N",
    "usecaptcha": "N",
}


def build(spec: dict) -> str:
    rows: list[dict] = []
    add = lambda **kw: rows.append({c: kw.get(c, "") for c in COLUMNS})  # noqa: E731

    for name, value in SURVEY_SETTINGS.items():
        add(**{"class": "S", "name": name, "text": value})
    for name, value in {
        "surveyls_title": spec["title"],
        "surveyls_description": spec["description"],
        "surveyls_welcometext": spec["welcome"],
        "surveyls_endtext": spec["end_text"],
    }.items():
        add(**{"class": "SL", "name": name, "text": value, "language": LANG})

    consent = spec["consent"]
    add(**{"class": "G", "name": "Consent", "relevance": "1", "language": LANG,
           "text": "Please read and confirm before you begin."})
    add(**{"class": "Q", "type/scale": "Y", "name": consent["code"], "relevance": "1",
           "text": consent["text"], "language": LANG, "mandatory": "Y", "other": "N",
           "help": "If you do not agree, simply close this page. Nothing will be submitted.",
           "em_validation_q": f"{consent['code']}.NAOK == 'Y'",
           "em_validation_q_tip": "You need to agree in order to take part."})

    group = None
    for q in spec["questions"]:
        if q["group"] != group:
            group = q["group"]
            add(**{"class": "G", "name": group, "relevance": "1", "language": LANG})
        qtype = "!" if q.get("display") == "dropdown" else QTYPES[q["type"]]
        row = {"class": "Q", "type/scale": qtype, "name": q["code"], "relevance": "1",
               "text": q["text"], "help": q.get("help", ""), "language": LANG,
               "mandatory": "Y" if q.get("required") else "N", "other": "N"}
        if q.get("max_answers"):
            row["max_answers"] = str(q["max_answers"])
        if q.get("max_length"):
            row["maximum_chars"] = str(q["max_length"])
        add(**row)
        child = "SQ" if q["type"] == "multi" else "A"
        for code, label in q.get("options", {}).items():
            add(**{"class": child, "type/scale": "0", "name": code, "text": label, "language": LANG})

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n",
                            quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as fh:
        sys.stdout.write(build(json.load(fh)))
