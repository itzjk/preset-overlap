import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .analyze import analyze


def quoted(value):
    return json.dumps(value, ensure_ascii=True)


def render(report):
    lines = [f"preset-overlap {__version__} | {report['status']}", ""]
    for info in report["inputs"]:
        lines.append(f"{info['id']}: {quoted(info['path'])} [{info['status']}]")
    lines.append("")
    rows = [["Adjustment", *[info["id"] for info in report["inputs"]], "Relationship"]]
    for field in report["fields"]:
        cells = []
        for cell in field["cells"]:
            if cell["state"] == "absent":
                cells.append(".")
            elif cell["state"] == "unavailable":
                cells.append("! unavailable")
            elif cell["state"] == "ambiguous":
                cells.append("? ambiguous")
            elif field["kind"] == "curve":
                cells.append(quoted(cell["occurrences"][0]["normalized"]))
            else:
                cells.append(quoted(cell["occurrences"][0]["literal"]))
        rows.append([field["name"], *cells, field["classification"]])
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    for row in rows:
        lines.append(" | ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip())
    summary = report["summary"]
    lines.extend(["", f"Shared fields: {summary['shared_fields']} ({summary['shared_equal']} equal, {summary['shared_different']} different, {sum(field['classification'] == 'ambiguous' and len(field['declared_in']) > 1 for field in report['fields'])} ambiguous)", ". = not declared; ? = no value selected. Argument order is reading order.", ""])
    if report["errors"]:
        lines.append("! = input unavailable; its declarations could not be inspected.\n")
    lines.append("Provenance (namespace aliases are fixed, independent of input prefixes)")
    for info in report["inputs"]:
        lines.append(f"{info['id']} SHA-256: {info['sha256'] or 'unavailable'}")
    for field in report["fields"]:
        for cell in field["cells"]:
            for entry in cell["occurrences"]:
                lines.append(f"{cell['input_id']} {field['name']} = {quoted(entry['literal'])} @ {entry['path']}")
                if "xml" in entry:
                    lines.append("  XML: " + quoted(entry["xml"]))
                if "error" in entry:
                    lines.append("  ambiguous: " + entry["error"])
                elif cell["state"] == "ambiguous":
                    lines.append("  ambiguous: duplicate property")
    lines.append("\nPreset metadata")
    metadata = [(info["id"], entry) for info in report["inputs"] for entry in info["metadata"]]
    for input_id, entry in metadata:
        lines.append(f"{input_id} {entry['name']} = {quoted(entry.get('xml', entry['literal']))} @ {entry['path']}")
    if not metadata:
        lines.append("None declared.")
    lines.append("\nCoverage pending")
    for entry in report["coverage_pending"]:
        lines.append(f"{entry['input_id']} {entry['name']} @ {entry['path']}: {entry['reason']}")
        lines.append("  Value: " + quoted(entry.get("xml", entry["literal"])))
    if not report["coverage_pending"]:
        lines.append("None.")
    if report["errors"]:
        lines.append("\nInvalid inputs")
        for error in report["errors"]:
            lines.append(f"{error['input_id']}: {quoted(error['message'])}")
    lines.append("\nExplicit declarations only. Shared fields do not establish visual compatibility.")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare explicitly declared global adjustments across local XMP presets.")
    parser.add_argument("presets", nargs="+", metavar="PRESET.xmp", help="explicit files, in reading order")
    parser.add_argument("--json", metavar="REPORT.json", type=Path, help="write a versioned report to a new file (never overwrite)")
    parser.add_argument("--version", action="version", version=f"preset-overlap {__version__}")
    args = parser.parse_args(argv)
    report = analyze(args.presets)
    if args.json:
        try:
            with args.json.open("x", encoding="utf-8") as output:
                output.write(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + "\n")
        except OSError as error:
            print(f"preset-overlap: cannot create report: {error}", file=sys.stderr)
            return 2
    try:
        print(render(report), end="")
    except BrokenPipeError:
        return {"complete": 0, "partial": 1, "invalid": 2}[report["status"]]
    return {"complete": 0, "partial": 1, "invalid": 2}[report["status"]]
