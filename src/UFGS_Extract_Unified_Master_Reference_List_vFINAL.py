# Auto-generated script from UFGS_Extract_Unified_Master_Reference_List_vFINAL.ipynb
# In[1]:
import csv
import re
import requests
import json
from pathlib import Path
from collections import defaultdict
from xml.etree import ElementTree as ET

UTF8_ARTIFACT_PATTERNS = {
    "Ã¢â‚¬â€œ": "–",
    "Ã¢â‚¬â€": "—",
    "Ã¢â‚¬Ëœ": "‘",
    "Ã¢â‚¬â„¢": "’",
    "Ã¢â‚¬Å“": "“",
    "Ã¢â‚¬ï¿½": '"',
    "Ã¢â‚¬Â": "”",
    "â€“": "–",
    "â€”": "—",
    "â€œ": "“",
    "â€": "”",
    "â€˜": "‘",
    "â€™": "’",
    "â€": "”",
}

def fix_windows1252_utf8_artifacts(text: str) -> str:
    for bad, good in UTF8_ARTIFACT_PATTERNS.items():
        text = text.replace(bad, good)
    text = re.sub(r'(\w)(—|–)(\w)', r'\1 \2 \3', text)
    return text

def clean_text(text: str) -> str:
    text = re.sub(r"<BRK\s*/?>", "", text)
    text = text.replace(" ", " ")
    text = text.replace("\u00AD", "")
    text = text.replace("\uFEFF", "")
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text).strip()

def extract_ref_blocks(raw_text: str) -> list:
    return re.findall(r"<REF>(.*?)</REF>", raw_text, flags=re.DOTALL)

def extract_org(block: str) -> str:
    org_match = re.search(r"<ORG>(.*?)</ORG>", block, flags=re.DOTALL)
    return fix_windows1252_utf8_artifacts(clean_text(org_match.group(1))) if org_match else ""

def extract_rid_rtl_pairs(block: str) -> list:
    pairs = re.findall(r"<RID>(.*?)</RID>\s*<RTL>(.*?)</RTL>", block, flags=re.DOTALL)
    return [(fix_windows1252_utf8_artifacts(clean_text(rid)),
             fix_windows1252_utf8_artifacts(clean_text(rtl))) for rid, rtl in pairs]

def parse_org_fields(org_full: str) -> dict:
    acronym_match = re.search(r"\(([^)]+)\)", org_full)
    if acronym_match:
        acronym = acronym_match.group(1).strip()
        name = org_full[:acronym_match.start()].strip()
    else:
        acronym = ""
        name = org_full
        print(f"⚠️ No acronym found in ORG: {org_full}")
    return {
        "Org_Full_Name": org_full,
        "Org_Name": name,
        "Org_Acronym": acronym,
    }

def write_csv(rows: list, out_path: Path, fieldnames: list):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def parse_revref_xml(xml_url: str) -> dict:
    response = requests.get(xml_url)
    response.raise_for_status()
    xml_content = response.content.decode("windows-1252", errors="replace")
    root = ET.fromstring(xml_content)

    rid_mapping = defaultdict(lambda: defaultdict(set))
    current_rid = None

    for txt in root.findall(".//TXT"):
        rid_elem = txt.find("RID")
        if rid_elem is not None:
            current_rid = rid_elem.text.strip()
        srf_elem = txt.find(".//SRF")
        if srf_elem is not None and current_rid:
            section = srf_elem.text.strip()
            for itm_elem in txt.findall(".//LST/ITM/ITM"):
                para = itm_elem.text.strip()
                rid_mapping[current_rid][section].add(para)

    # Convert sets to sorted lists
    return {rid: {sec: sorted(paras) for sec, paras in sec_map.items()}
            for rid, sec_map in rid_mapping.items()}

def parse_master_ref_and_add_revref():
    # 1️⃣ Parse REVREF.LST.xml
    revref_mapping = parse_revref_xml("https://raw.githubusercontent.com/vdubya/criteria-assistant/main/lib/REVREF.LST.xml")

    # 2️⃣ Parse MASTER.REF.XML
    response = requests.get("https://raw.githubusercontent.com/vdubya/criteria-assistant/main/lib/MASTER.REF.XML")
    response.raise_for_status()
    raw_text = response.content.decode("windows-1252", errors="replace")
    ref_blocks = extract_ref_blocks(raw_text)

    unique_orgs = {}
    for block in ref_blocks:
        org_full = extract_org(block)
        if org_full and org_full not in unique_orgs:
            org_info = parse_org_fields(org_full)
            unique_orgs[org_full] = org_info

    sorted_orgs = sorted(unique_orgs.values(), key=lambda o: o["Org_Acronym"])
    org_details = []
    org_lookup = {}
    for i, org_info in enumerate(sorted_orgs, start=1):
        org_id = f"ORG{i:03}"
        org_info["Org_ID"] = org_id
        org_details.append(org_info)
        org_lookup[org_info["Org_Full_Name"]] = org_id

    # 3️⃣ Build set of initial URML list (all RIDs)
    urml_rids = set()
    for block in ref_blocks:
        rid_rtl_list = extract_rid_rtl_pairs(block)
        for rid, _ in rid_rtl_list:
            urml_rids.add(rid)

    # 4️⃣ Collect record rows, build Spec_References JSON, and track stats
    rows = []
    rids_with_refs = set()
    rids_without_refs = set()
    for block in ref_blocks:
        org_full = extract_org(block)
        if not org_full:
            continue
        org_info = next((o for o in org_details if o["Org_Full_Name"] == org_full), {})
        rid_rtl_list = extract_rid_rtl_pairs(block)
        for rid, rtl in rid_rtl_list:
            spec_refs = revref_mapping.get(rid, {})
            if not spec_refs:
                print(f"⚠️ RID '{rid}' has no spec references in REVREF.LST.xml.")
                rids_without_refs.add(rid)
            else:
                rids_with_refs.add(rid)
            for section in spec_refs.keys():
                if rid not in urml_rids:
                    print(f"⚠️ Section '{section}' for RID '{rid}' not found in initial URML list.")
            spec_refs_json = json.dumps(spec_refs, ensure_ascii=False)
            rows.append({
                "RID": rid,
                "Title": rtl,
                "Org_Acronym": org_info.get("Org_Acronym"),
                "Org_Name": org_info.get("Org_Name"),
                "Org_ID": org_info.get("Org_ID"),
                "Spec_References": spec_refs_json
            })

    rows.sort(key=lambda x: x["RID"])

    write_csv(
        rows,
        Path("/content/URML.csv"),
        fieldnames=["RID", "Title", "Org_Acronym", "Org_Name", "Org_ID", "Spec_References"]
    )

    write_csv(
        org_details,
        Path("/content/URML-orgs.csv"),
        fieldnames=["Org_ID", "Org_Acronym", "Org_Name", "Org_Full_Name"]
    )

    print(f"✅ Parsed {len(rows):,} RID/RTL records from {len(ref_blocks):,} <REF> blocks")
    print(f"✅ Unique organizations: {len(org_details)}")
    print(f"✅ Unique RIDs: {len(urml_rids)}")
    print(f"✅ RIDs with spec references: {len(rids_with_refs)}")
    print(f"✅ RIDs without spec references: {len(rids_without_refs)}")
    print(f"✔ Final URML.csv file saved: /content/URML.csv")
    print(f"✔ Final URML-orgs.csv file saved: /content/URML-orgs.csv")

# ✅ Run it
parse_master_ref_and_add_revref()
