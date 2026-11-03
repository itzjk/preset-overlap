from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from preset_overlap.analyze import MAX_BYTES, MAX_DEPTH, MAX_NODES, analyze
from preset_overlap.cli import render
from preset_overlap.fields import CRS, KINDS, RDF

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [ROOT / "examples" / name for name in ("color.xmp", "grain.xmp", "finish.xmp")]


def xmp(attributes="", elements="", prefix="crs", namespace=CRS):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="{RDF}">
    <rdf:Description rdf:about="" xmlns:{prefix}="{namespace}" {attributes}>
      {elements}
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>'''


def write(tmp_path, name, content):
    path = tmp_path / name
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    return path


def field(report, name):
    return next(item for item in report["fields"] if item["name"] == name)


def run_cli(*args, cwd=None):
    return subprocess.run([sys.executable, "-m", "preset_overlap", *map(str, args)], cwd=cwd, capture_output=True, text=True, timeout=15)


def test_reproduction_matrix():
    report = analyze(EXAMPLES)
    assert report["status"] == "complete"
    assert report["summary"] == {"fields": 3, "shared_fields": 2, "exclusive": 1, "shared_equal": 1, "shared_different": 1, "ambiguous": 0, "pending": 0}
    exposure = field(report, "Exposure2012")
    assert exposure["classification"] == "shared_equal"
    assert [cell["state"] for cell in exposure["cells"]] == ["declared", "absent", "declared"]
    assert exposure["cells"][0]["occurrences"][0]["literal"] == "0.30"
    assert field(report, "Contrast2012")["classification"] == "shared_different"
    assert field(report, "GrainAmount")["classification"] == "exclusive"


def test_prefix_only_changes_hash(tmp_path):
    path = write(tmp_path, "preset.xmp", xmp('crs:Exposure2012="0.30"'))
    original = analyze([path])
    path.write_text(xmp('adjust:Exposure2012="0.30"', prefix="adjust"))
    renamed = analyze([path])
    assert original["inputs"][0]["sha256"] != renamed["inputs"][0]["sha256"]
    original["inputs"][0]["sha256"] = renamed["inputs"][0]["sha256"]
    original["inputs"][0]["size_bytes"] = renamed["inputs"][0]["size_bytes"]
    assert original == renamed


def test_remove_contrast_removes_only_its_overlap(tmp_path):
    grain = write(tmp_path, "grain.xmp", EXAMPLES[1].read_text().replace('crs:Contrast2012="0" ', ""))
    report = analyze([EXAMPLES[0], grain, EXAMPLES[2]])
    assert report["summary"]["shared_fields"] == 1
    assert field(report, "Contrast2012")["classification"] == "exclusive"
    assert field(report, "Exposure2012")["classification"] == "shared_equal"
    assert field(report, "GrainAmount")["classification"] == "exclusive"


@pytest.mark.parametrize("attribute,element", [("0.30", "0.3"), ("-0", "0.00"), ("+10.0", "10"), (".300", "0.3"), ("123456789012345678901234567890.01", "123456789012345678901234567890.010")])
def test_decimal_equivalence_attribute_and_element(tmp_path, attribute, element):
    paths = [write(tmp_path, "a.xmp", xmp(f'crs:Exposure2012="{attribute}"')), write(tmp_path, "b.xmp", xmp(elements=f"<crs:Exposure2012>{element}</crs:Exposure2012>"))]
    report = analyze(paths)
    assert report["status"] == "complete"
    assert field(report, "Exposure2012")["classification"] == "shared_equal"
    assert field(report, "Exposure2012")["cells"][1]["occurrences"][0]["path"].endswith("/crs:Exposure2012[1]")


def test_absent_is_not_zero(tmp_path):
    paths = [write(tmp_path, "a.xmp", xmp('crs:Contrast2012="0"')), write(tmp_path, "b.xmp", xmp('crs:GrainAmount="20"'))]
    contrast = field(analyze(paths), "Contrast2012")
    assert contrast["classification"] == "exclusive"
    assert contrast["cells"][1] == {"input_id": "p2", "state": "absent", "occurrences": []}


def test_three_way_same_values(tmp_path):
    paths = [write(tmp_path, f"{index}.xmp", xmp(f'crs:Exposure2012="{value}"')) for index, value in enumerate(["0.30", "0.3", "+.300"])]
    exposure = field(analyze(paths), "Exposure2012")
    assert exposure["classification"] == "shared_equal"
    assert exposure["declared_in"] == ["p1", "p2", "p3"]


def test_same_local_name_wrong_uri_is_not_camera_raw(tmp_path):
    path = write(tmp_path, "other.xmp", xmp('crs:Exposure2012="0.3"', namespace="urn:other"))
    report = analyze([path, EXAMPLES[0]])
    assert field(report, "Exposure2012")["classification"] == "exclusive"
    assert field(report, "Exposure2012")["cells"][0]["state"] == "absent"


@pytest.mark.parametrize("a,b,classification", [("True", "1", "shared_equal"), ("false", "0", "shared_equal"), ("True", "False", "shared_different"), ("TRUE", "True", "ambiguous")])
def test_explicit_boolean_table(tmp_path, a, b, classification):
    paths = [write(tmp_path, "a.xmp", xmp(f'crs:ConvertToGrayscale="{a}"')), write(tmp_path, "b.xmp", xmp(elements=f"<crs:ConvertToGrayscale>{b}</crs:ConvertToGrayscale>"))]
    assert field(analyze(paths), "ConvertToGrayscale")["classification"] == classification


def curve(points, name="ToneCurvePV2012"):
    return f"<crs:{name}><rdf:Seq>" + "".join(f"<rdf:li>{point}</rdf:li>" for point in points) + f"</rdf:Seq></crs:{name}>"


@pytest.mark.parametrize("points,classification", [(["0,0", "255,255"], "shared_equal"), (["0.0, 0", "255.00,255"], "shared_equal"), (["255,255", "0,0"], "shared_different"), (["0,0", "255,254"], "shared_different")])
def test_curves_use_ordered_decimal_points(tmp_path, points, classification):
    paths = [write(tmp_path, "a.xmp", xmp(elements=curve(["0, 0", "255, 255"]))), write(tmp_path, "b.xmp", xmp(elements=curve(points)))]
    report = analyze(paths)
    assert report["status"] == "complete"
    result = field(report, "ToneCurvePV2012")
    assert result["classification"] == classification
    assert result["cells"][0]["occurrences"][0]["xml"]["children"][0]["children"][0]["text"] == "0, 0"


@pytest.mark.parametrize("elements", ["<crs:ToneCurvePV2012/>", "<crs:ToneCurvePV2012><rdf:Seq/></crs:ToneCurvePV2012>", "<crs:ToneCurvePV2012><rdf:Bag><rdf:li>0,0</rdf:li></rdf:Bag></crs:ToneCurvePV2012>", curve(["not a point"]), '<crs:Exposure2012 rdf:resource="anything"/>'])
def test_unknown_representation_stays_visible(tmp_path, elements):
    path = write(tmp_path, "structured.xmp", xmp('crs:Contrast2012="10"', elements))
    report = analyze([path])
    assert report["status"] == "partial"
    assert report["summary"]["ambiguous"] == 1
    assert report["coverage_pending"]
    assert field(report, "Contrast2012")["classification"] == "exclusive"


def test_curve_attribute_is_ambiguous_and_pending(tmp_path):
    path = write(tmp_path, "curve.xmp", xmp('crs:ToneCurvePV2012="0,0"'))
    report = analyze([path])
    assert report["status"] == "partial"
    assert field(report, "ToneCurvePV2012")["classification"] == "ambiguous"
    assert report["coverage_pending"][0]["name"] == "ToneCurvePV2012"


@pytest.mark.parametrize("value", ["10", "0"])
def test_attribute_and_element_duplicates_never_choose_a_value(tmp_path, value):
    path = write(tmp_path, "repeat.xmp", xmp('crs:Contrast2012="10"', f"<crs:Contrast2012>{value}</crs:Contrast2012>"))
    report = analyze([path, EXAMPLES[1]])
    contrast = field(report, "Contrast2012")
    assert report["status"] == "partial"
    assert contrast["classification"] == "ambiguous"
    assert contrast["cells"][0]["state"] == "ambiguous"
    assert len(contrast["cells"][0]["occurrences"]) == 2
    assert "duplicate property" in render(report)


def test_repeated_elements_have_distinct_paths(tmp_path):
    path = write(tmp_path, "repeat.xmp", xmp(elements="<crs:Exposure2012>1</crs:Exposure2012><crs:Exposure2012>2</crs:Exposure2012>"))
    occurrences = field(analyze([path]), "Exposure2012")["cells"][0]["occurrences"]
    assert occurrences[0]["path"].endswith("[1]")
    assert occurrences[1]["path"].endswith("[2]")


def test_unknown_properties_profiles_and_masks_keep_known_results(tmp_path):
    path = write(tmp_path, "unknown.xmp", xmp('crs:Exposure2012="0.3" crs:CameraProfile="Adobe Color" crs:FutureSlider="4"', '<crs:MaskGroup><rdf:Seq><rdf:li crs:Contrast2012="20"/></rdf:Seq></crs:MaskGroup>'))
    report = analyze([path, EXAMPLES[0]])
    assert report["status"] == "partial"
    assert field(report, "Exposure2012")["classification"] == "shared_equal"
    assert field(report, "Contrast2012")["cells"][0]["state"] == "absent"
    assert {item["name"] for item in report["coverage_pending"]} == {"CameraProfile", "FutureSlider", "MaskGroup", "Contrast2012"}
    assert all(item["input_id"] == "p1" and item["path"] for item in report["coverage_pending"])


@pytest.mark.parametrize("version,status", [("11.0", "complete"), ("99.0", "partial")])
def test_process_version_is_metadata_and_unknown_is_partial(tmp_path, version, status):
    path = write(tmp_path, "metadata.xmp", xmp(f'crs:UUID="own-fixture" crs:ProcessVersion="{version}"', '<crs:Name><rdf:Alt><rdf:li xml:lang="x-default">Sample</rdf:li></rdf:Alt></crs:Name>'))
    report = analyze([path])
    assert report["status"] == status
    assert not report["fields"]
    assert {item["name"] for item in report["inputs"][0]["metadata"]} == {"UUID", "ProcessVersion", "Name"}


def test_duplicate_metadata_is_partial(tmp_path):
    path = write(tmp_path, "metadata.xmp", xmp('crs:UUID="one"', '<crs:UUID>two</crs:UUID>'))
    report = analyze([path])
    assert report["status"] == "partial"
    assert len(report["coverage_pending"]) == 2


def test_duplicate_unknown_properties_are_explicitly_ambiguous(tmp_path):
    path = write(tmp_path, "unknown.xmp", xmp('crs:CameraProfile="one"', '<crs:CameraProfile>two</crs:CameraProfile>'))
    report = analyze([path])
    assert report["status"] == "partial"
    assert len(report["coverage_pending"]) == 2
    assert all(item["ambiguous"] and "ambiguous duplicate" in item["reason"] for item in report["coverage_pending"])


def test_analysis_does_not_use_network_or_write_inputs(tmp_path, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    path = write(tmp_path, "offline.xmp", xmp('crs:Exposure2012="0.3"'))
    before = path.read_bytes()
    assert analyze([path])["status"] == "complete"
    assert path.read_bytes() == before


def test_utf16_xml_with_dtd_is_rejected(tmp_path):
    xml = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE root><root/>'
    path = write(tmp_path, "utf16.xmp", xml.encode("utf-16"))
    report = analyze([path])
    assert report["status"] == "invalid"
    assert "DTDForbidden" in report["errors"][0]["message"]


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1e1000000", "", "1,2", "1_000", "--1"])
def test_invalid_decimal_is_ambiguous(tmp_path, value):
    path = write(tmp_path, "decimal.xmp", xmp(f'crs:Exposure2012="{value}"'))
    report = analyze([path])
    assert report["status"] == "partial"
    assert field(report, "Exposure2012")["classification"] == "ambiguous"


@pytest.mark.parametrize("content", ["<broken", "<root/>", '<!DOCTYPE root><root/>', '<!DOCTYPE root [<!ENTITY v "0.3">]><root>&v;</root>', '<!DOCTYPE root SYSTEM "https://example.invalid/no"><root/>'])
def test_invalid_and_forbidden_xml(tmp_path, content):
    path = write(tmp_path, "invalid.xmp", content)
    report = analyze([path, EXAMPLES[0]])
    assert report["status"] == "invalid"
    assert report["errors"]
    assert report["inputs"][0]["sha256"] == sha256(path.read_bytes()).hexdigest()
    assert field(report, "Exposure2012")


def test_missing_file_keeps_valid_results(tmp_path):
    report = analyze([tmp_path / "missing.xmp", EXAMPLES[0]])
    assert report["status"] == "invalid"
    assert report["inputs"][0]["sha256"] is None
    assert field(report, "Exposure2012")
    assert field(report, "Exposure2012")["cells"][0]["state"] == "unavailable"
    assert "! unavailable" in render(report)


def test_invalid_input_cannot_establish_absence(tmp_path):
    path = write(tmp_path, "broken.xmp", '<rdf:RDF xmlns:rdf="' + RDF + '"><rdf:Description')
    report = analyze([path, EXAMPLES[0]])
    assert field(report, "Exposure2012")["classification"] == "exclusive"
    assert field(report, "Exposure2012")["declared_in"] == ["p2"]
    assert field(report, "Exposure2012")["cells"][0] == {"input_id": "p1", "state": "unavailable", "occurrences": []}


# Short, explicit ids: the inputs are multi-megabyte blobs, and pytest puts the nodeid into the
# PYTEST_CURRENT_TEST environment variable. Without fixed ids the blob lands in that value, and
# Windows rejects an environment variable longer than 32767 characters (every case errors at setup).
@pytest.mark.parametrize("content,fragment", [(b" " * (MAX_BYTES + 1), "bytes"), (("<a>" * (MAX_DEPTH + 1) + "</a>" * (MAX_DEPTH + 1)).encode(), "depth"), (("<a>" + "<b/>" * MAX_NODES + "</a>").encode(), "count")], ids=["bytes", "depth", "count"])
def test_resource_limits(tmp_path, content, fragment):
    path = write(tmp_path, "limit.xmp", content)
    report = analyze([path])
    assert report["status"] == "invalid"
    assert fragment in report["errors"][0]["message"]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO")
def test_fifo_is_rejected_without_blocking(tmp_path):
    path = tmp_path / "pipe.xmp"
    os.mkfifo(path)
    assert run_cli(path).returncode == 2


def test_cli_terminal_json_hashes_and_argument_order(tmp_path):
    before = [path.read_bytes() for path in EXAMPLES]
    output = tmp_path / "report.json"
    paths = [EXAMPLES[2], EXAMPLES[0], EXAMPLES[1]]
    result = run_cli(*paths, "--json", output)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report["schema_version"] == "1.0"
    assert result.stdout == render(report)
    assert [info["path"] for info in report["inputs"]] == list(map(str, paths))
    for info in report["inputs"]:
        assert info["sha256"] == sha256(Path(info["path"]).read_bytes()).hexdigest()
        assert info["sha256"] in result.stdout
    assert [path.read_bytes() for path in EXAMPLES] == before
    for item in report["fields"]:
        assert item["name"] in result.stdout and item["classification"] in result.stdout


def test_reports_are_repeatable(tmp_path):
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    assert run_cli(*EXAMPLES, "--json", first).returncode == 0
    assert run_cli(*EXAMPLES, "--json", second).returncode == 0
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize("content,code,status", [(xmp('crs:FutureSlider="3"'), 1, "partial"), ("<broken", 2, "invalid")])
def test_exit_codes_keep_json(tmp_path, content, code, status):
    path = write(tmp_path, "input.xmp", content)
    output = tmp_path / "report.json"
    result = run_cli(path, EXAMPLES[0], "--json", output)
    assert result.returncode == code
    report = json.loads(output.read_text())
    assert report["status"] == status
    assert "Exposure2012" in result.stdout


@pytest.mark.parametrize("alias", ["same", "hardlink", "symlink"])
def test_output_never_overwrites_inputs(tmp_path, alias):
    source = write(tmp_path, "preset.xmp", EXAMPLES[0].read_bytes())
    output = source if alias == "same" else tmp_path / "report.json"
    if alias == "hardlink":
        os.link(source, output)
    if alias == "symlink":
        try:
            output.symlink_to(source)
        except OSError:
            pytest.skip("symlink privilege unavailable")
    before = source.read_bytes()
    result = run_cli(source, "--json", output)
    assert result.returncode == 2
    assert "cannot create report" in result.stderr
    assert source.read_bytes() == before


def test_control_characters_are_escaped(tmp_path):
    path = write(tmp_path, "input.xmp", xmp('crs:FutureSlider="one&#10;two"'))
    result = run_cli(path)
    assert 'one\\ntwo' in result.stdout


def test_all_supported_fields_have_documented_names():
    documentation = (ROOT / "docs" / "coverage.md").read_text()
    assert all(name in documentation for name in KINDS)
