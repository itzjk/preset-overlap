from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import os
import re
import stat
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from .fields import BOOLEAN_VALUES, CRS, KINDS, METADATA, NAMESPACES, PROCESS_VERSIONS, RDF

MAX_BYTES = 4 * 1024 * 1024
MAX_DEPTH = 64
MAX_NODES = 50000
DECIMAL_PATTERN = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z")


def qname(namespace, name):
    return "{" + namespace + "}" + name


def split_name(tag):
    if tag.startswith("{"):
        return tag[1:].split("}", 1)
    return "", tag


def display_name(tag):
    uri, name = split_name(tag)
    for prefix, namespace in NAMESPACES.items():
        if uri == namespace:
            return prefix + ":" + name
    return tag


def decimal_value(literal):
    value = literal.strip()
    if not DECIMAL_PATTERN.fullmatch(value):
        raise ValueError("expected a finite decimal without exponent")
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("expected a finite decimal") from error
    if number == 0:
        return "0"
    result = format(number, "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def tree_value(node):
    return {
        "tag": node.tag,
        "attributes": dict(sorted(node.attrib.items())),
        "text": node.text,
        "tail": node.tail,
        "children": [tree_value(child) for child in node],
    }


def parse_xml(data):
    depth = 0
    nodes = 0
    parser = ElementTree.iterparse(
        BytesIO(data), events=("start", "end"),
        forbid_dtd=True, forbid_entities=True, forbid_external=True,
    )
    for event, _ in parser:
        if event == "start":
            depth += 1
            nodes += 1
            if depth > MAX_DEPTH:
                raise ValueError(f"XML depth exceeds {MAX_DEPTH}")
            if nodes > MAX_NODES:
                raise ValueError(f"XML element count exceeds {MAX_NODES}")
        else:
            depth -= 1
    return parser.root


def walk(node, path, parent=None):
    yield node, path, parent
    counts = Counter()
    for child in node:
        counts[child.tag] += 1
        child_path = f"{path}/{display_name(child.tag)}[{counts[child.tag]}]"
        yield from walk(child, child_path, node)


def global_descriptions(root, nodes):
    rdf_nodes = {id(root)} if root.tag == qname(RDF, "RDF") else set()
    if root.tag == qname(NAMESPACES["x"], "xmpmeta"):
        rdf_nodes.update(id(child) for child in root if child.tag == qname(RDF, "RDF"))
    return {
        id(node) for node, _, parent in nodes
        if node.tag == qname(RDF, "Description")
        and parent is not None and id(parent) in rdf_nodes
    }


def normalize(kind, node, literal):
    if kind == "curve":
        if node is None or node.attrib or (node.text or "").strip() or len(node) != 1:
            raise ValueError("expected one unqualified rdf:Seq")
        seq = node[0]
        if seq.tag != qname(RDF, "Seq") or seq.attrib or (seq.text or "").strip() or (seq.tail or "").strip() or not len(seq):
            raise ValueError("expected a nonempty rdf:Seq of points")
        points = []
        for item in seq:
            if item.tag != qname(RDF, "li") or item.attrib or len(item) or (item.tail or "").strip():
                raise ValueError("expected simple rdf:li points")
            parts = (item.text or "").split(",")
            if len(parts) != 2:
                raise ValueError("expected comma-separated x,y points")
            points.append([decimal_value(part) for part in parts])
        return points
    if node is not None and (len(node) or node.attrib):
        raise ValueError("expected an unqualified scalar element")
    if kind == "decimal":
        return decimal_value(literal)
    if literal.strip() not in BOOLEAN_VALUES:
        raise ValueError("boolean must be True, False, true, false, 1 or 0")
    return BOOLEAN_VALUES[literal.strip()]


def read_input(path):
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("input must be a regular file")
        data = source.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"input exceeds {MAX_BYTES} bytes; hash not computed")
    return data


def inspect_input(path, input_id):
    info = {"id": input_id, "path": str(path), "sha256": None, "size_bytes": None, "status": "complete", "metadata": []}
    adjustments = defaultdict(list)
    pending = []
    errors = []
    try:
        data = read_input(path)
        info.update(sha256=sha256(data).hexdigest(), size_bytes=len(data))
        root = parse_xml(data)
        nodes = list(walk(root, "/" + display_name(root.tag) + "[1]"))
        descriptions = global_descriptions(root, nodes)
        if not descriptions:
            raise ValueError("expected rdf:RDF with a top-level rdf:Description")
    except (OSError, ValueError, ParseError, DefusedXmlException) as error:
        info["status"] = "invalid"
        errors.append({"input_id": input_id, "message": str(error)})
        return info, adjustments, pending, errors

    property_counts = Counter()
    for node, _, parent in nodes:
        if parent is not None and id(parent) in descriptions and split_name(node.tag)[0] == CRS:
            property_counts[split_name(node.tag)[1]] += 1
        if id(node) in descriptions:
            property_counts.update(split_name(tag)[1] for tag in node.attrib if split_name(tag)[0] == CRS)

    def collect(tag, location, literal, node, global_property):
        uri, name = split_name(tag)
        if uri != CRS:
            return
        occurrence = {"path": location, "representation": "attribute" if node is None else "element", "literal": literal}
        if global_property and property_counts[name] > 1:
            occurrence["ambiguous"] = True
        if node is not None and (len(node) or node.attrib):
            occurrence["xml"] = tree_value(node)
        if global_property and name in METADATA:
            info["metadata"].append({"name": name, **occurrence})
            simple = node is None or not len(node) and not node.attrib
            if name != "ProcessVersion" or simple and literal.strip() in PROCESS_VERSIONS:
                return
            reason = "unrecognized process version; settings are compared structurally only"
        elif not global_property:
            reason = "outside a global rdf:Description property; not interpreted as a global adjustment"
        elif name not in KINDS:
            reason = "unsupported Camera Raw property"
        else:
            try:
                occurrence["normalized"] = normalize(KINDS[name], node, literal)
            except ValueError as error:
                occurrence["error"] = str(error)
                pending.append({
                    "input_id": input_id, "namespace": uri, "name": name,
                    "reason": "uninterpretable value or representation of a known adjustment",
                    **occurrence,
                })
            adjustments[name].append(occurrence)
            return
        if occurrence.get("ambiguous"):
            reason = "ambiguous duplicate property; " + reason
        pending.append({"input_id": input_id, "namespace": uri, "name": name, "reason": reason, **occurrence})

    for node, location, parent in nodes:
        if split_name(node.tag)[0] == CRS:
            collect(node.tag, location, node.text or "", node, parent is not None and id(parent) in descriptions)
        for tag, value in sorted(node.attrib.items()):
            collect(tag, location + "/@" + display_name(tag), value, None, id(node) in descriptions)

    metadata_counts = Counter(entry["name"] for entry in info["metadata"])
    for name, count in sorted(metadata_counts.items()):
        if count > 1:
            for entry in info["metadata"]:
                if entry["name"] == name:
                    pending.append({"input_id": input_id, "namespace": CRS, "reason": "duplicate metadata property", **entry})
    if pending or any(len(values) != 1 or "error" in values[0] for values in adjustments.values()):
        info["status"] = "partial"
    return info, adjustments, pending, errors


def analyze(paths):
    inputs, declarations, pending, errors = [], [], [], []
    for index, path in enumerate(paths, 1):
        info, values, uncovered, failures = inspect_input(path, f"p{index}")
        inputs.append(info)
        declarations.append(values)
        pending.extend(uncovered)
        errors.extend(failures)
    fields = []
    for name in sorted({name for values in declarations for name in values}):
        cells = []
        for info, values in zip(inputs, declarations):
            occurrences = values.get(name, [])
            if info["status"] == "invalid":
                state = "unavailable"
            elif not occurrences:
                state = "absent"
            elif len(occurrences) != 1 or "error" in occurrences[0]:
                state = "ambiguous"
            else:
                state = "declared"
            cells.append({"input_id": info["id"], "state": state, "occurrences": occurrences})
        present = [cell for cell in cells if cell["state"] in {"declared", "ambiguous"}]
        normalized = [cell["occurrences"][0].get("normalized") for cell in present]
        if any(cell["state"] == "ambiguous" for cell in present):
            classification = "ambiguous"
        elif len(present) == 1:
            classification = "exclusive"
        elif all(value == normalized[0] for value in normalized):
            classification = "shared_equal"
        else:
            classification = "shared_different"
        fields.append({"namespace": CRS, "name": name, "kind": KINDS[name], "classification": classification, "declared_in": [cell["input_id"] for cell in present], "cells": cells})
    counts = Counter(field["classification"] for field in fields)
    status = "invalid" if errors else "partial" if any(info["status"] == "partial" for info in inputs) else "complete"
    return {
        "schema_version": "1.0",
        "status": status,
        "namespaces": NAMESPACES,
        "inputs": inputs,
        "fields": fields,
        "summary": {"fields": len(fields), "shared_fields": sum(len(field["declared_in"]) > 1 for field in fields), **{key: counts[key] for key in ("exclusive", "shared_equal", "shared_different", "ambiguous")}, "pending": len(pending)},
        "coverage_pending": pending,
        "errors": errors,
    }
