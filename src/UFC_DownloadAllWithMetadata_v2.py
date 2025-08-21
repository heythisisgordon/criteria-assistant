# Auto-generated script from UFC_DownloadAllWithMetadata_v2.ipynb
# In[1]:
# =======================
# Step 0: Install dependencies
# =======================
# !pip install requests beautifulsoup4

# =======================
# Step 1: Imports and Config
# =======================
import requests
from bs4 import BeautifulSoup
import json
import csv
import re
import os
import time
import zipfile
from datetime import datetime
from urllib.parse import urlparse

# =======================
# Config Flags
# =======================
DEBUG_LEVEL = 2
PARTIAL_RUN = False
FORCE_DOWNLOAD = False
METADATA_ONLY = False
FILENAME_SUFFIX_DATE = False
STATUS_FILTERS = {"Active", "Inactive", "Archived", "Reference"}
RUN_UNIT_TESTS = False

BASE_URL = "https://www.wbdg.org"
URLS = {
    "active_page1": "https://www.wbdg.org/dod/ufc?field_status_value=1&field_series_value=All",
    "active_page2": "https://www.wbdg.org/dod/ufc?field_status_value=1&field_series_value=All&page=1",
    "inactive": "https://www.wbdg.org/dod/ufc?field_status_value=2&field_series_value=All",
    "archived": "https://www.wbdg.org/dod/ufc?field_status_value=3&field_series_value=All"
}

ufc_complete_downloads = [
    ("UFC Complete Volume 1", "https://www.wbdg.org/FFC/DOD/UFC/UFC_Complete_1-200-01_thru_3-220-20.pdf"),
    ("UFC Complete Volume 2", "https://www.wbdg.org/FFC/DOD/UFC/UFC_Complete_3-230-01_thru_3-340-02.pdf"),
    ("UFC Complete Volume 3", "https://www.wbdg.org/FFC/DOD/UFC/UFC_Complete_3-400-02_thru_3-810-01N.pdf"),
    ("UFC Complete Volume 4", "https://www.wbdg.org/FFC/DOD/UFC/UFC_Complete_4-010-01_thru_4-159-03.pdf"),
    ("UFC Complete Volume 5", "https://www.wbdg.org/FFC/DOD/UFC/UFC_Complete_FC_4-171-06N_thru_4-860_03.pdf")
]

def debug(msg, level=1):
    if DEBUG_LEVEL >= level:
        print(f"[DEBUG] {msg}")

def parse_title_fields(raw_title):
    if "Replaced by" in raw_title:
        parts = raw_title.split("Replaced by")
        main_part, replaced_by = parts[0].strip().rstrip(","), "Replaced by " + parts[1].strip()
    else:
        main_part, replaced_by = raw_title, None
    match = re.match(r"^(UFC|FC)\s+([\d\-A-Z]+)\s+(.*)", main_part)
    return {
        "ufc_prefix": match.group(1) if match else None,
        "ufc_number": match.group(2) if match else None,
        "title": match.group(3) if match else main_part,
        "replaced_by": replaced_by
    }

def detect_ufc_type_from_url(url):
    basename = os.path.basename(url)
    if basename.upper().startswith("FC"):
        return "FC"
    elif basename.upper().startswith("UFC"):
        return "UFC"
    return "Unknown"

def fetch_metadata(detail_url, ufc_number=None):
    response = requests.get(detail_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    full_name = soup.find("h1", class_="page-title").text.strip()

    if full_name.strip().lower() == "ufc complete":
        debug(f"⏭️ Skipped parsing for UFC Complete at: {detail_url}", 1)
        return None

    metadata = {
        "ufc_full_name": full_name
    }

    if not ufc_number:
        m = re.search(r'(UFC|FC)\s+(\d-\d{3}-\d{2}[A-Z]*)', metadata["ufc_full_name"])
        if m:
            ufc_number = m.group(2)
            metadata["ufc_type"] = m.group(1)
    metadata["ufc_number"] = ufc_number
    metadata["ufc_type"] = metadata.get("ufc_type") or "UFC"
    metadata["ufc_title"] = metadata["ufc_full_name"].replace(f"{metadata['ufc_type']} {ufc_number} ", "") if ufc_number else metadata["ufc_full_name"]

    status_div = soup.select_one('div.field--name-field-status .field__item')
    metadata["status"] = status_div.text.strip() if status_div else "Unknown"

    pub_time = soup.select_one('div.field--name-field-published-date .field__item time')
    metadata["publish_date"] = pub_time.text.strip() if pub_time else None

    change_time = soup.select_one('div.field--name-field-cngrevdt .field__item time')
    metadata["change_date"] = change_time.text.strip() if change_time else None

    pages_div = soup.select_one('div.field--name-field-pages .field__item')
    metadata["pages"] = int(pages_div.text.strip()) if pages_div and pages_div.text.strip().isdigit() else None

    series_items = soup.select('div.field--name-field-series .field__item')
    metadata["series"] = " | ".join(item.text.strip() for item in series_items) if series_items else None

    link_tag = soup.select_one('div.field--name-field-viewdown a[href$=".pdf"]')
    if link_tag:
        download_url = BASE_URL + link_tag['href']
        filename = os.path.basename(link_tag['href'])
    else:
        download_url = None
        filename = None

    metadata["download_link"] = download_url
    metadata["filename"] = filename
    metadata["metadata_link"] = detail_url

    summary_div = soup.select_one('div.field--name-field-summary .field__item')
    metadata["summary"] = summary_div.get_text(strip=True) if summary_div else ""

    metadata["ccr_url"] = f"https://cms.wbdg.org/ccrs/new?ufc={ufc_number}" if ufc_number else None

    metadata["superseded_versions"] = []
    superseded_divs = soup.select('div.field--name-field-supervers .field__item')
    for div in superseded_divs:
        a_tag = div.find("a")
        date_tag = div.find("small")
        if a_tag:
            href = BASE_URL + a_tag["href"]
            title = a_tag.get_text(strip=True).replace(u'\xa0', ' ')
            date = date_tag.get_text(strip=True).strip("()") if date_tag else None
            metadata["superseded_versions"].append({
                "title": title,
                "url": href,
                "date": date,
                "filename": os.path.basename(href)  # <--- ✅ Added here
            })

    metadata["superseded_versions_count"] = len(metadata["superseded_versions"])

    if metadata["ufc_number"] == "1-200-01":
        run_tests(metadata)

    return metadata

def scrape_ufc_list(url):
    debug(f"[INFO] Scraping UFC list from: {url}", 1)
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.find_all("tr")
    entries = []

    for i, row in enumerate(rows[:10] if PARTIAL_RUN else rows):
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        raw_title = cols[0].get_text(strip=True)
        parsed = parse_title_fields(raw_title)
        detail_url = BASE_URL + cols[0].find("a")["href"]

        metadata = fetch_metadata(detail_url, ufc_number=parsed["ufc_number"])
        if not metadata:
            continue

        entry = {
            "ufc_full_name": metadata["ufc_full_name"],
            "ufc_number": metadata["ufc_number"],
            "ufc_prefix": parsed["ufc_prefix"],
            "ufc_title": metadata["ufc_title"],
            "ufc_type": metadata["ufc_type"],
            "filename": metadata["filename"],  # <--- ✅ Added here
            "pages": metadata.get("pages"),
            "series": metadata.get("series"),
            "status": metadata["status"],
            "publish_date": metadata["publish_date"],
            "change_date": metadata["change_date"],
            "archived / rescinded date": None,
            "replaced_by": parsed["replaced_by"],
            "download_link": metadata["download_link"],
            "metadata_link": metadata["metadata_link"],
            "summary": metadata["summary"],
            "ccr_url": metadata["ccr_url"],
            "superseded_versions": metadata["superseded_versions"],
            "superseded_versions_count": metadata["superseded_versions_count"]
        }

        debug(json.dumps(entry, indent=2), level=2)
        entries.append(entry)
        time.sleep(0.25)

    return entries

# In[2]:
def run_tests(metadata):
    debug("🔍 Running unit tests for UFC 1-200-01...", 1)

    def assert_equal(field, actual, expected):
        if actual != expected:
            raise AssertionError(f"[FAIL] {field} mismatch:\n  - Expected: {expected}\n  - Actual:   {actual}")
        debug(f"[PASS] {field}: {actual}", 2)

    assert_equal("ufc_number", metadata["ufc_number"], "1-200-01")
    assert metadata["ufc_type"].startswith(("UFC", "FC")), f"[FAIL] ufc_type: {metadata['ufc_type']} must start with 'UFC' or 'FC'"
    debug(f"[PASS] ufc_type: {metadata['ufc_type']}", 2)

    assert_equal("status", metadata["status"], "Active")
    assert_equal("ufc_full_name", metadata["ufc_full_name"], "UFC 1-200-01 DoD Building Code, with Change 4")
    assert_equal("ufc_title", metadata["ufc_title"], "DoD Building Code, with Change 4")
    assert_equal("download_link", metadata["download_link"], "https://www.wbdg.org/FFC/DOD/UFC/ufc_1_200_01_2022_c4.pdf")
    assert_equal("filename", metadata["filename"], "ufc_1_200_01_2022_c4.pdf")
    assert_equal("metadata_link", metadata["metadata_link"], "https://www.wbdg.org/dod/ufc/ufc-1-200-01")
    assert_equal("change_date", metadata["change_date"], "12/17/2024")
    assert_equal("publish_date", metadata["publish_date"], "09/01/2022")
    assert_equal("superseded_versions_count", metadata["superseded_versions_count"], 21)

    expected_titles = [
        "UFC 1-200-01 DoD Building Code, with Change 3",
        "UFC 1-200-01 DoD Building Code, with Change 2",
        "UFC 1-200-01 DoD Building Code, with Change 1",
        "UFC 1-200-01 DoD Building Code",
        "UFC 1-200-01 DoD Building Code, with Change 1",
        "UFC 1-200-01 DoD Building Code",
        "UFC 1-200-01 DoD Building Code (General Building Requirements), with Change 2",
        "UFC 1-200-01 DoD Building Code (General Building Requirements), with Change 1",
        "UFC 1-200-01 DoD Building Code (General Building Requirements)",
        "UFC 1-200-01 General Building Requirements, with Change 3",
        "UFC 1-200-01 General Building Requirements, with Change 2",
        "UFC 1-200-01 General Building Requirements, with Change 1",
        "UFC 1-200-01 General Building Requirements",
        "UFC 1-200-01 General Building Requirements, with Change 2",
        "UFC 1-200-01 General Building Requirements, with Change 1",
        "UFC 1-200-01 General Building Requirements",
        "UFC 1-200-01 General Building Requirements, with Change 2",
        "UFC 1-200-01 General Building Requirements, with Change 1",
        "UFC 1-200-01 General Building Requirements",
        "UFC 1-200-01 General Building Requirements",
        "UFC 1-200-01 General Building Requirements"
    ]

    expected_dates = [
        "02-26-2024", "06-12-2023", "02-24-2023", "09-01-2022", "10-01-2020", "10-08-2019",
        "11-01-2018", "02-01-2018", "06-20-2016", "08-01-2015", "11-01-2014", "09-01-2013",
        "07-01-2013", "11-28-2011", "07-19-2011", "07-01-2010", "01-27-2010", "05-07-2009",
        "07-01-2007", "07-01-2005", "07-31-2002"
    ]

    expected_filenames = [
        "ufc_1_200_01_2022_c3.pdf", "ufc_1_200_01_2022_c2.pdf", "ufc_1_200_01_2022_c1.pdf", "ufc_1_200_01_2022.pdf",
        "ufc_1_200_01_2019_c1.pdf", "ufc_1_200_01_2019.pdf", "ufc_1_200_01_2016_c2.pdf", "ufc_1_200_01_2016_c1.pdf",
        "ufc_1_200_01_2016.pdf", "ufc_1_200_01_2013_c3.pdf", "ufc_1_200_01_2013_c2.pdf", "ufc_1_200_01_2013_c1.pdf",
        "ufc_1_200_01_2013.pdf", "ufc_1_200_01_2010_c2.pdf", "ufc_1_200_01_2010_c1.pdf", "ufc_1_200_01_2010.pdf",
        "ufc_1_200_01_2007_c2.pdf", "ufc_1_200_01_2007_c1.pdf", "ufc_1_200_01_2007.pdf", "ufc_1_200_01_2005.pdf",
        "ufc_1_200_01_2002.pdf"
    ]

    for i, version in enumerate(metadata["superseded_versions"]):
        try:
            assert_equal(f"superseded_versions[{i}].title", version["title"], expected_titles[i])
            assert_equal(f"superseded_versions[{i}].date", version["date"], expected_dates[i])
            assert_equal(f"superseded_versions[{i}].filename", version["filename"], expected_filenames[i])
        except AssertionError as e:
            raise AssertionError(f"Superseded version mismatch at index {i}:\n{str(e)}")

    debug("✅ Unit tests passed for UFC 1-200-01.", 1)

# =======================
# Main Execution
# =======================
if RUN_UNIT_TESTS:
    metadata = fetch_metadata("https://www.wbdg.org/dod/ufc/ufc-1-200-01")
    debug(json.dumps(metadata, indent=2), level=1)
else:
    all_ufcs = []
    for url in URLS.values():
        all_ufcs += scrape_ufc_list(url)

    for name, url in ufc_complete_downloads:
        all_ufcs.append({
            "ufc_full_name": name,
            "ufc_number": None,
            "ufc_prefix": None,
            "ufc_title": name,
            "ufc_type": "UFC",
            "filename": os.path.basename(url),
            "pages": None,
            "series": None,
            "status": "Reference",
            "publish_date": "06/02/2025",
            "change_date": None,
            "archived / rescinded date": None,
            "replaced_by": None,
            "download_link": url,
            "metadata_link": "https://www.wbdg.org/dod/ufc/ufc-complete",
            "summary": "Active UFCs combined into five PDF documents",
            "ccr_url": None,
            "superseded_versions": [],
            "superseded_versions_count": 0
        })

    # === JSON Output ===
    with open("wbdg_ufc_metadata.json", "w", encoding="utf-8") as f:
        json.dump(all_ufcs, f, indent=2, ensure_ascii=False)

    # === CSV Output (flattened) ===
    def flatten(entry):
        flat_entry = entry.copy()
        flat_entry["superseded_version_titles"] = "|".join(
            [str(v.get("title", "") or "") for v in entry.get("superseded_versions", [])]
        )
        flat_entry["superseded_version_dates"] = "|".join(
            [str(v.get("date", "") or "") for v in entry.get("superseded_versions", [])]
        )
        flat_entry.pop("superseded_versions", None)
        return flat_entry

    flattened = [flatten(e) for e in all_ufcs]

    csv_fieldnames = list(flattened[0].keys())
    with open("wbdg_ufc_metadata.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        writer.writeheader()
        writer.writerows(flattened)

    # === Optional PDF Download + ZIP ===
    if not METADATA_ONLY:
        os.makedirs("wbdg_ufc_downloads", exist_ok=True)
        total_files = sum(1 for e in all_ufcs if e.get("download_link"))

        for idx, entry in enumerate(all_ufcs, start=1):
            url = entry["download_link"]
            if not url:
                continue
            filename = os.path.basename(urlparse(url).path)
            if FILENAME_SUFFIX_DATE and entry.get("change_date"):
                try:
                    dt = datetime.strptime(entry["change_date"], "%m-%d-%Y")
                    filename = f"{entry['ufc_number']} [{dt.date()}].pdf"
                except:
                    pass
            status_dir = os.path.join("wbdg_ufc_downloads", (entry["status"] or "Unknown").capitalize())
            os.makedirs(status_dir, exist_ok=True)
            filepath = os.path.join(status_dir, filename)

            if FORCE_DOWNLOAD or not os.path.exists(filepath):
                try:
                    file_data = requests.get(url).content
                    with open(filepath, "wb") as f:
                        f.write(file_data)
                    debug(f"[{idx}/{total_files}] ✅ Downloaded: {filename}", 1)
                except Exception as e:
                    debug(f"[{idx}/{total_files}] ❌ Failed download: {filename} — {e}", 1)
            else:
                debug(f"[{idx}/{total_files}] ⏭️ Skipped (exists): {filename}", 1)

        # Create ZIP and include metadata files at root
        with zipfile.ZipFile("wbdg_ufc_downloads.zip", "w") as zipf:
            zipf.write("wbdg_ufc_metadata.json")
            zipf.write("wbdg_ufc_metadata.csv")
            for root, _, files in os.walk("wbdg_ufc_downloads"):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, start="wbdg_ufc_downloads")
                    zipf.write(full_path, arcname=arcname)

        debug("📦 All UFC files and metadata zipped.", 1)
    else:
        debug("✅ Metadata-only mode complete.", 1)
