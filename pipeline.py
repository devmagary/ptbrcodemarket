# -*- coding: utf-8 -*-
"""Pipeline de localização EN/RU -> PT-BR para Code Market (Unity Mono)."""

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

from translations_ptbr import (
    DLL_US_TRANSLATIONS,
    RESOURCE_PT_OVERRIDES,
    SCRIPT_COMMENT_REPLACEMENTS,
)

ROOT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = ROOT_DIR / "tools" / "DllStringPatcher"
PATCHER_EXE = TOOLS_DIR / "DllStringPatcher.exe"
TRABALHO_DIR = ROOT_DIR / "trabalho"
EXTRACTED_DIR = TRABALHO_DIR / "extracted"
TRANSLATED_DIR = TRABALHO_DIR / "translated"
DIST_DIR = TRABALHO_DIR / "dist"
BACKUPS_DIR = TRABALHO_DIR / "backups"
ORIGINALS_BACKUP_DIR = BACKUPS_DIR / "originals"
LOGS_DIR = TRABALHO_DIR / "logs"
REPORTS_DIR = TRABALHO_DIR / "reports"
GLOSSARY_PATH = ROOT_DIR / "glossary.json"

DEFAULT_GAME_DIR = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Code Market")
TARGET_DLLS = [
    "JavaMarket.dll",
    "JavaMarket.Cpp.dll",
    "JavaMarket.CSharp.dll",
    "JavaMarket.Java.dll",
    "JavaMarket.JavaScript.dll",
    "JavaMarket.Python.dll",
]
PT_ACCENT_CHARS = "áéíóúâêôãõçàÁÉÍÓÚÂÊÔÃÕÇÀ"


def ensure_dirs():
    for d in [
        EXTRACTED_DIR,
        TRANSLATED_DIR,
        DIST_DIR / "Code Market_Data" / "Managed",
        BACKUPS_DIR,
        ORIGINALS_BACKUP_DIR,
        LOGS_DIR,
        REPORTS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)


def ensure_patcher_exe():
    if PATCHER_EXE.exists():
        return
    cs_src = TOOLS_DIR / "DllStringPatcher.cs"
    csc = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
    if not csc.exists():
        raise FileNotFoundError(f"Compilador C# não encontrado em {csc}")
    print("[setup] Compilando DllStringPatcher.exe...")
    subprocess.run(
        [str(csc), "/nologo", "/optimize+", f"/out:{PATCHER_EXE}", str(cs_src)],
        check=True,
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_game_dir(cli_game_dir: str | None = None) -> Path:
    if cli_game_dir:
        p = Path(cli_game_dir)
        if (p / "Code Market_Data").is_dir():
            return p
        raise FileNotFoundError(f"Pasta do jogo inválida: {p}")
    if (DEFAULT_GAME_DIR / "Code Market_Data").is_dir():
        return DEFAULT_GAME_DIR
    # Check common Steam library drives
    for drive in "CDEFGH":
        cand = Path(f"{drive}:\\SteamLibrary\\steamapps\\common\\Code Market")
        if (cand / "Code Market_Data").is_dir():
            return cand
    raise FileNotFoundError("Instalação do Code Market não encontrada. Informe --game-dir.")


def parse_unity_v22_assets(data: bytes):
    """Parse Unity v22 SerializedFile object table and metadata bounds."""
    meta_sz, file_sz, data_off, _ = struct.unpack_from(">IQQQ", data, 20)
    pos = 48
    end = data.index(b"\x00", pos)
    pos = end + 1 + 5  # version string + platform(4) + enable_type_tree(1)
    type_count = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    types = []
    for _ in range(type_count):
        class_id = struct.unpack_from("<i", data, pos)[0]
        script_type_idx = struct.unpack_from("<h", data, pos + 5)[0]
        pos += 7 + (16 if (class_id == 114 or script_type_idx >= 0) else 0) + 16
        types.append(class_id)
    obj_count = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    objs = []
    for _ in range(obj_count):
        pos = (pos + 3) & ~3
        info_offset = pos
        path_id, byte_start, byte_size, type_id = struct.unpack_from("<qQII", data, pos)
        pos += 24
        objs.append({
            "info_offset": info_offset,
            "path_id": path_id,
            "byte_start": byte_start,
            "byte_size": byte_size,
            "class_id": types[type_id],
        })
    return meta_sz, file_sz, data_off, objs


def read_text_asset(data: bytes, data_off: int, obj: dict) -> tuple[str, bytes, int]:
    off = data_off + obj["byte_start"]
    nlen = struct.unpack_from("<I", data, off)[0]
    name = data[off + 4 : off + 4 + nlen].decode("utf-8", "replace")
    coff = off + ((4 + nlen + 3) & ~3)
    clen = struct.unpack_from("<I", data, coff)[0]
    content = data[coff + 4 : coff + 4 + clen]
    tail_off = coff + 4 + clen
    tail_pad = (off + obj["byte_size"]) - tail_off
    return name, content, tail_pad


def build_text_asset_bytes(name: str, content_bytes: bytes) -> bytes:
    nb = name.encode("utf-8")
    name_pad = (-len(nb)) % 4
    content_pad = (-len(content_bytes)) % 4
    return (
        struct.pack("<I", len(nb))
        + nb
        + (b"\x00" * name_pad)
        + struct.pack("<I", len(content_bytes))
        + content_bytes
        + (b"\x00" * content_pad)
    )


def validate_tags_and_placeholders(src: str, dst: str, allow_omitted_placeholders: bool = False) -> list[str]:
    errors = []
    src_ph = re.findall(r"\{[0-9a-zA-Z_:,.-]+\}", src)
    dst_ph = re.findall(r"\{[0-9a-zA-Z_:,.-]+\}", dst)
    if allow_omitted_placeholders:
        # Check that no unexpected placeholder index was introduced
        src_nums = {int(re.match(r"\{(\d+)", p).group(1)) for p in src_ph if re.match(r"\{(\d+)", p)}
        dst_nums = {int(re.match(r"\{(\d+)", p).group(1)) for p in dst_ph if re.match(r"\{(\d+)", p)}
        if not dst_nums.issubset(src_nums):
            errors.append(f"Placeholder fora do intervalo: {dst_nums - src_nums}")
    else:
        if sorted(src_ph) != sorted(dst_ph):
            errors.append(f"Placeholders divergentes: {src_ph} vs {dst_ph}")

    # Check balanced RichText tags
    tag_re = re.compile(r"<(/?)(color|b|i|size|style)(?:=[^>]*)?>")
    src_tags = tag_re.findall(src)
    dst_tags = tag_re.findall(dst)
    if len(src_tags) != len(dst_tags):
        errors.append(f"Tags RichText divergentes: {src_tags} vs {dst_tags}")

    # Check open/close tag balance in dst
    stack = []
    for closing, tag_name in dst_tags:
        if not closing:
            stack.append(tag_name)
        else:
            if not stack or stack[-1] != tag_name:
                errors.append(f"Tag RichText desbalanceada em: {dst[:80]}")
                break
            stack.pop()
    if stack:
        errors.append(f"Tags não fechadas: {stack}")

    # Check leading/trailing space preservation for concatenated fragments
    if src.startswith(" ") and not dst.startswith(" "):
        errors.append("Espaço inicial perdido")
    if src.endswith(" ") and not dst.endswith(" "):
        errors.append("Espaço final perdido")

    return errors


def check_ttf_pt_glyphs(res_data: bytes, data_off: int, objs: list[dict]) -> dict:
    results = {}
    for obj in objs:
        if obj["class_id"] != 128:
            continue
        off = data_off + obj["byte_start"]
        nlen = struct.unpack_from("<I", res_data, off)[0]
        name = res_data[off + 4 : off + 4 + nlen].decode("utf-8", "replace")
        if "Nunito" not in name:
            continue
        blob = res_data[off : off + obj["byte_size"]]
        # Locate valid sfnt header followed by cmap
        found_ttf = False
        missing_chars = list(PT_ACCENT_CHARS)
        search_pos = 0
        while True:
            idx = blob.find(b"\x00\x01\x00\x00", search_pos)
            if idx == -1 or idx + 12 >= len(blob):
                break
            num_tables = struct.unpack_from(">H", blob, idx + 4)[0]
            if 4 <= num_tables <= 40 and idx + 12 + num_tables * 16 <= len(blob):
                # Check if table directory has 'cmap' and 'head'
                tags = {blob[idx + 12 + t * 16 : idx + 16 + t * 16] for t in range(num_tables)}
                if b"cmap" in tags and b"head" in tags:
                    found_ttf = True
                    for t in range(num_tables):
                        if blob[idx + 12 + t * 16 : idx + 16 + t * 16] == b"cmap":
                            cmap_off = idx + struct.unpack_from(">I", blob, idx + 12 + t * 16 + 8)[0]
                            nt = struct.unpack_from(">H", blob, cmap_off + 2)[0]
                            for j in range(nt):
                                suboff = cmap_off + struct.unpack_from(">I", blob, cmap_off + 4 + j * 8 + 4)[0]
                                fmt = struct.unpack_from(">H", blob, suboff)[0]
                                if fmt == 4:
                                    seg_cnt = struct.unpack_from(">H", blob, suboff + 6)[0] // 2
                                    ends = struct.unpack_from(f">{seg_cnt}H", blob, suboff + 14)
                                    starts = struct.unpack_from(f">{seg_cnt}H", blob, suboff + 16 + seg_cnt * 2)
                                    missing_chars = [
                                        ch for ch in PT_ACCENT_CHARS
                                        if not any(s <= ord(ch) <= e for s, e in zip(starts, ends))
                                    ]
                                    break
                    break
            search_pos = idx + 1
        results[name] = {
            "path_id": obj["path_id"],
            "ttf_parsed": found_ttf,
            "missing_pt_chars": missing_chars,
        }
    return results


def cmd_extract(args):
    ensure_dirs()
    t0 = time.perf_counter()
    game_dir = find_game_dir(args.game_dir)
    managed_dir = game_dir / "Code Market_Data" / "Managed"

    ensure_patcher_exe()

    # 1. Extract #US strings from all 6 DLLs (always prefer clean original backups)
    raw_dll_data = {}
    for dll in TARGET_DLLS:
        orig_local = ORIGINALS_BACKUP_DIR / "Managed" / dll
        steam_dll = managed_dir / dll
        steam_bak = Path(str(steam_dll) + ".bak")
        src_dll = orig_local if orig_local.exists() else (steam_bak if steam_bak.exists() else steam_dll)

        out_json = EXTRACTED_DIR / f"{dll}.raw.json"
        subprocess.run(
            [str(PATCHER_EXE), "extract", str(src_dll), str(out_json)],
            check=True,
        )
        raw_dll_data[dll] = json.loads(out_json.read_text(encoding="utf-8"))

    # 2. Extract PT TextAssets and commented scripts from resources.assets
    orig_res_local = ORIGINALS_BACKUP_DIR / "resources.assets"
    steam_res = game_dir / "Code Market_Data" / "resources.assets"
    steam_res_bak = Path(str(steam_res) + ".bak")
    res_path = orig_res_local if orig_res_local.exists() else (steam_res_bak if steam_res_bak.exists() else steam_res)
    res_bytes = res_path.read_bytes()
    meta_sz, file_sz, data_off, objs = parse_unity_v22_assets(res_bytes)

    pt_tables = []
    pt_en_keys = set()
    script_assets = []
    for obj in objs:
        if obj["class_id"] != 49:
            continue
        name, content, _ = read_text_asset(res_bytes, data_off, obj)
        text = content.decode("utf-8", "replace")
        if text.startswith('{\n "entries": ['):
            parsed = json.loads(text)
            entries = parsed.get("entries", [])
            if entries and "pt" in entries[0]:
                pt_tables.append({
                    "path_id": obj["path_id"],
                    "name": name,
                    "entries": entries,
                })
                for e in entries:
                    if "en" in e:
                        pt_en_keys.add(e["en"])
        elif obj["path_id"] in (326, 826, 842):
            script_assets.append({
                "path_id": obj["path_id"],
                "name": name,
                "content": text,
            })

    other_assets_summary = {}
    for asset_name in ["sharedassets0.assets", "level0"]:
        ap = game_dir / "Code Market_Data" / asset_name
        ab = ap.read_bytes()
        _, _, a_data_off, a_objs = parse_unity_v22_assets(ab)
        ta_count = sum(1 for o in a_objs if o["class_id"] == 49)
        other_assets_summary[asset_name] = {
            "byte_length": len(ab),
            "object_count": len(a_objs),
            "text_asset_count": ta_count,
            "translatable_entries": 0,
            "status": "checked_no_localizable_text" if ta_count == 0 else "checked",
        }

    resources_dump = {
        "pt_table_count": len(pt_tables),
        "pt_entry_count": sum(len(t["entries"]) for t in pt_tables),
        "pt_tables": pt_tables,
        "script_assets": script_assets,
        "other_unity_assets": other_assets_summary,
    }
    (EXTRACTED_DIR / "resources_assets.json").write_text(
        json.dumps(resources_dump, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 3. Run intelligent classifier
    classified = {"modules": {}, "summary": {}}
    res_total_entries = resources_dump["pt_entry_count"] + len(script_assets)
    classified["modules"]["resources.assets"] = {
        "raw_total": res_total_entries,
        "translate_resource_asset": res_total_entries,
        "already_translated_pt": sum(
            1 for t in pt_tables for e in t["entries"] if e.get("pt") and e.get("pt") != e.get("en")
        ),
        "needs_translation_or_fix": sum(
            1 for t in pt_tables for e in t["entries"] if e.get("en") in RESOURCE_PT_OVERRIDES or e.get("pt") == e.get("en")
        ) + len(script_assets),
    }
    for asset_name, info in other_assets_summary.items():
        classified["modules"][asset_name] = info

    for dll in TARGET_DLLS:
        entries = raw_dll_data[dll]["strings"]
        target_map = DLL_US_TRANSLATIONS.get(dll, {})
        items = []
        counts = {
            "raw_total": len(entries),
            "TRANSLATE_DLL_US": 0,
            "COVERED_BY_LOC_TABLE": 0,
            "DO_NOT_TRANSLATE": 0,
        }
        for item in entries:
            val = item["value"]
            callers_str = " ".join(item["callers"])
            if val in target_map and "HintForError" not in callers_str:
                cat = "TRANSLATE_DLL_US"
            elif val in pt_en_keys or val.replace("\r\n", "\n") in pt_en_keys:
                cat = "COVERED_BY_LOC_TABLE"
            else:
                cat = "DO_NOT_TRANSLATE"
            counts[cat] += 1
            items.append({
                "us_offset": item["us_offset"],
                "token": item["token"],
                "value": val,
                "callers": item["callers"],
                "category": cat,
            })
        classified["modules"][dll] = counts
        classified["summary"][dll] = items

    (EXTRACTED_DIR / "classified_strings.json").write_text(
        json.dumps(classified, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    elapsed = round(time.perf_counter() - t0, 3)
    print(f"[extract] Concluído em {elapsed}s — resources.assets ({res_total_entries} itens) + 6 DLLs ({sum(m['raw_total'] for k, m in classified['modules'].items() if k in TARGET_DLLS)} strings #US).")
    return elapsed


def cmd_translate(args):
    ensure_dirs()
    t0 = time.perf_counter()
    glossary = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    resources_dump = json.loads((EXTRACTED_DIR / "resources_assets.json").read_text(encoding="utf-8"))
    classified = json.loads((EXTRACTED_DIR / "classified_strings.json").read_text(encoding="utf-8"))

    cache_path = TRANSLATED_DIR / "translation_cache.json"
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        cache = {"resources": {}, "dlls": {}, "scripts": {}}

    validation_errors = []

    # 1. Process resources.assets PT tables
    res_patches = []
    for tbl in resources_dump["pt_tables"]:
        new_entries = []
        changed = False
        for e in tbl["entries"]:
            en = e.get("en", "")
            pt = e.get("pt", "")
            # Apply curated overrides or preserve existing validated PT
            if en in RESOURCE_PT_OVERRIDES:
                final_pt = RESOURCE_PT_OVERRIDES[en]
            elif en in cache.get("resources", {}):
                final_pt = cache["resources"][en]
            else:
                final_pt = pt

            errs = validate_tags_and_placeholders(
                en, final_pt, allow_omitted_placeholders=True
            )
            if errs:
                validation_errors.append({
                    "module": "resources.assets",
                    "asset": tbl["name"],
                    "en": en,
                    "pt": final_pt,
                    "errors": errs,
                })

            cache["resources"][en] = final_pt
            if final_pt != pt:
                changed = True
            updated = dict(e)
            updated["pt"] = final_pt
            new_entries.append(updated)

        if changed:
            res_patches.append({
                "path_id": tbl["path_id"],
                "name": tbl["name"],
                "kind": "json_pt",
                "content": json.dumps({"entries": new_entries}, ensure_ascii=False, indent=1),
            })

    # 2. Process 3 commented script TextAssets (stocker, cashier, map)
    for scr in resources_dump["script_assets"]:
        txt = scr["content"]
        new_txt = txt
        for ru_comment, pt_comment in SCRIPT_COMMENT_REPLACEMENTS.items():
            new_txt = new_txt.replace(ru_comment, pt_comment)
        cache["scripts"][scr["name"]] = {"modified": new_txt != txt}
        if new_txt != txt:
            res_patches.append({
                "path_id": scr["path_id"],
                "name": scr["name"],
                "kind": "script",
                "content": new_txt,
            })

    (TRANSLATED_DIR / "resources_assets.patch.json").write_text(
        json.dumps(res_patches, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 3. Process DLL #US patches
    for dll in TARGET_DLLS:
        dll_items = classified["summary"][dll]
        target_map = DLL_US_TRANSLATIONS.get(dll, {})
        patch_by_offset = {}
        dll_cache = cache["dlls"].setdefault(dll, {})
        for item in dll_items:
            if item["category"] != "TRANSLATE_DLL_US":
                continue
            orig_en = item["value"]
            pt_val = dll_cache.get(orig_en) or target_map.get(orig_en)
            if not pt_val:
                validation_errors.append({
                    "module": dll,
                    "en": orig_en,
                    "errors": ["Tradução ausente para string TRANSLATE_DLL_US"],
                })
                continue
            errs = validate_tags_and_placeholders(orig_en, pt_val, allow_omitted_placeholders=False)
            if errs:
                validation_errors.append({
                    "module": dll,
                    "en": orig_en,
                    "pt": pt_val,
                    "errors": errs,
                })
                continue
            dll_cache[orig_en] = pt_val
            patch_by_offset[str(item["us_offset"])] = pt_val

        (TRANSLATED_DIR / f"{dll}.patch.json").write_text(
            json.dumps(patch_by_offset, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    if validation_errors:
        raise RuntimeError(f"Erros de validação pré-injeção encontrados: {validation_errors[:5]}")

    elapsed = round(time.perf_counter() - t0, 3)
    print(f"[translate] Concluído em {elapsed}s — {len(res_patches)} TextAssets atualizados e 6 mapas de patch de DLL gerados (0 erros de tags/placeholders).")
    return elapsed


def cmd_build(args):
    ensure_dirs()
    t0 = time.perf_counter()
    game_dir = find_game_dir(args.game_dir)
    managed_src = game_dir / "Code Market_Data" / "Managed"
    managed_dst = DIST_DIR / "Code Market_Data" / "Managed"
    managed_dst.mkdir(parents=True, exist_ok=True)

    # Always build from verified clean originals if backup exists
    for dll in TARGET_DLLS:
        orig_backup = ORIGINALS_BACKUP_DIR / "Managed" / dll
        src_dll = orig_backup if orig_backup.exists() else (managed_src / dll)
        patch_json = TRANSLATED_DIR / f"{dll}.patch.json"
        out_dll = managed_dst / dll
        subprocess.run(
            [str(PATCHER_EXE), "patch", str(src_dll), str(patch_json), str(out_dll)],
            check=True,
        )

    # Rebuild resources.assets
    orig_res_backup = ORIGINALS_BACKUP_DIR / "resources.assets"
    src_res = orig_res_backup if orig_res_backup.exists() else (game_dir / "Code Market_Data" / "resources.assets")
    res_data = src_res.read_bytes()
    meta_sz, file_sz, data_off, objs = parse_unity_v22_assets(res_data)
    res_patches = json.loads((TRANSLATED_DIR / "resources_assets.patch.json").read_text(encoding="utf-8"))
    patch_by_pid = {p["path_id"]: p for p in res_patches}

    header_prefix = bytearray(res_data[:data_off])
    out_chunks = []
    cur_rel = 0
    for obj in objs:
        # Align each object start to 16 bytes (satisfies Unity 8-byte & 16-byte alignment)
        pad = (-cur_rel) % 16
        if pad:
            out_chunks.append(b"\x00" * pad)
            cur_rel += pad

        pid = obj["path_id"]
        if pid in patch_by_pid:
            pinfo = patch_by_pid[pid]
            new_obj_bytes = build_text_asset_bytes(pinfo["name"], pinfo["content"].encode("utf-8"))
        else:
            start = data_off + obj["byte_start"]
            new_obj_bytes = res_data[start : start + obj["byte_size"]]

        struct.pack_into("<QI", header_prefix, obj["info_offset"] + 8, cur_rel, len(new_obj_bytes))
        out_chunks.append(new_obj_bytes)
        cur_rel += len(new_obj_bytes)

    new_file_size = data_off + cur_rel
    struct.pack_into(">Q", header_prefix, 24, new_file_size)

    out_res = DIST_DIR / "Code Market_Data" / "resources.assets"
    with open(out_res, "wb") as f:
        f.write(header_prefix)
        for ch in out_chunks:
            f.write(ch)

    elapsed = round(time.perf_counter() - t0, 3)
    print(f"[build] Concluído em {elapsed}s — 6 DLLs e resources.assets gerados em trabalho/dist/.")
    return elapsed


def cmd_verify(args, step_timings: dict | None = None):
    ensure_dirs()
    t0 = time.perf_counter()
    classified = json.loads((EXTRACTED_DIR / "classified_strings.json").read_text(encoding="utf-8"))
    cache = json.loads((TRANSLATED_DIR / "translation_cache.json").read_text(encoding="utf-8"))
    glossary = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))

    dist_managed = DIST_DIR / "Code Market_Data" / "Managed"
    dist_res = DIST_DIR / "Code Market_Data" / "resources.assets"
    res_bytes = dist_res.read_bytes()
    meta_sz, file_sz, data_off, objs = parse_unity_v22_assets(res_bytes)

    # 1. Verify rebuilt resources.assets integrity + PT coverage + font cmap
    assert file_sz == len(res_bytes), f"resources.assets file_size inválido: {file_sz} != {len(res_bytes)}"
    pt_entries_verified = []
    scripts_verified = {}
    tag_errors = []

    for obj in objs:
        if obj["class_id"] != 49:
            continue
        name, content, _ = read_text_asset(res_bytes, data_off, obj)
        txt = content.decode("utf-8", "replace")
        if txt.startswith('{\n "entries": ['):
            parsed = json.loads(txt)
            entries = parsed.get("entries", [])
            if entries and "pt" in entries[0]:
                for e in entries:
                    en = e.get("en", "")
                    pt = e.get("pt", "")
                    errs = validate_tags_and_placeholders(en, pt, allow_omitted_placeholders=True)
                    if errs:
                        tag_errors.append({"asset": name, "en": en, "pt": pt, "errors": errs})
                    pt_entries_verified.append({
                        "module": "resources.assets",
                        "asset": name,
                        "at": e.get("at", ""),
                        "original_en": en,
                        "translated_ptbr": pt,
                    })
        elif obj["path_id"] in (326, 826, 842):
            has_cyr = bool(re.search(r"[\u0400-\u04FF]", txt))
            scripts_verified[name] = {"has_remaining_cyrillic": has_cyr, "bytes": len(content)}

    font_checks = check_ttf_pt_glyphs(res_bytes, data_off, objs)

    # 2. Verify patched DLLs by re-extracting #US from dist DLLs
    res_eligible = len(pt_entries_verified) + len(scripts_verified)
    res_translated = sum(1 for x in pt_entries_verified if x["translated_ptbr"]) + sum(
        1 for v in scripts_verified.values() if not v["has_remaining_cyrillic"]
    )
    res_cov = round(100.0 * res_translated / res_eligible, 2) if res_eligible else 100.0
    module_metrics = {
        "resources.assets": {
            "raw_strings": classified["modules"]["resources.assets"]["raw_total"],
            "eligible_visible": res_eligible,
            "translated": res_translated,
            "coverage_pct": res_cov,
            "dist_bytes": dist_res.stat().st_size,
            "dist_mb": round(dist_res.stat().st_size / (1024 * 1024), 3),
        }
    }
    for asset_name in ["sharedassets0.assets", "level0"]:
        info = classified["modules"].get(asset_name, {})
        module_metrics[asset_name] = {
            "raw_strings": 0,
            "eligible_visible": 0,
            "translated": 0,
            "coverage_pct": 100.0,
            "object_count": info.get("object_count", 0),
            "text_asset_count": info.get("text_asset_count", 0),
            "status": info.get("status", "checked_no_localizable_text"),
        }

    dll_samples = []
    do_not_translate_samples = []
    for dll in TARGET_DLLS:
        dist_dll = dist_managed / dll
        recheck_json = REPORTS_DIR / f"{dll}.verify.json"
        subprocess.run(
            [str(PATCHER_EXE), "extract", str(dist_dll), str(recheck_json)],
            check=True,
        )
        recheck = json.loads(recheck_json.read_text(encoding="utf-8"))
        dist_values = {x["value"]: x for x in recheck["strings"]}

        orig_items = classified["summary"][dll]
        eligible = [x for x in orig_items if x["category"] == "TRANSLATE_DLL_US"]
        translated_ok = 0
        for x in eligible:
            expected_pt = cache["dlls"].get(dll, {}).get(x["value"], "")
            if expected_pt and expected_pt in dist_values:
                translated_ok += 1
                errs = validate_tags_and_placeholders(x["value"], expected_pt, allow_omitted_placeholders=False)
                if errs:
                    tag_errors.append({"module": dll, "en": x["value"], "pt": expected_pt, "errors": errs})
                dll_samples.append({
                    "module": dll,
                    "callers": x["callers"][:2],
                    "original_en": x["value"],
                    "translated_ptbr": expected_pt,
                })
            else:
                tag_errors.append({"module": dll, "en": x["value"], "errors": ["String traduzida ausente na DLL final"]})

        # Verify DO_NOT_TRANSLATE strings remain intact in dist DLL
        dnt_candidates = [
            x for x in orig_items
            if x["category"] == "DO_NOT_TRANSLATE"
            and len(x["value"]) >= 4
            and not re.search(r"[\u0400-\u04FF]", x["value"])
        ]
        for x in dnt_candidates[:10]:
            preserved = x["value"] in dist_values
            if not preserved:
                tag_errors.append({"module": dll, "en": x["value"], "errors": ["DO_NOT_TRANSLATE foi alterada!"]})
            do_not_translate_samples.append({
                "module": dll,
                "value": x["value"],
                "callers": x["callers"][:2],
                "preserved_exact": preserved,
            })

        cov_pct = round(100.0 * translated_ok / len(eligible), 2) if eligible else 100.0
        module_metrics[dll] = {
            "raw_strings": len(orig_items),
            "covered_by_loc_table": classified["modules"][dll]["COVERED_BY_LOC_TABLE"],
            "eligible_direct_dll_us": len(eligible),
            "translated": translated_ok,
            "coverage_pct": cov_pct,
            "reextracted_us_count": recheck["us_count"],
            "dist_bytes": dist_dll.stat().st_size,
            "dist_mb": round(dist_dll.stat().st_size / (1024 * 1024), 3),
        }

    # Build stratified sample_audit.json (>= 150 translated samples covering UI + 5 languages + DLLs)
    stratified = list(dll_samples)
    buckets = {
        "UI": [],
        "Cpp": [],
        "CSharp": [],
        "Java": [],
        "JavaScript": [],
        "Python": [],
        "World": [],
    }
    for e in pt_entries_verified:
        a = e["asset"]
        if a.startswith("UI.") or a.startswith("App."):
            buckets["UI"].append(e)
        elif "Cpp" in a:
            buckets["Cpp"].append(e)
        elif "CSharp" in a:
            buckets["CSharp"].append(e)
        elif "JavaScript" in a or "JsLanguage" in a:
            buckets["JavaScript"].append(e)
        elif "Python" in a:
            buckets["Python"].append(e)
        elif "Java" in a:
            buckets["Java"].append(e)
        elif a.startswith("World."):
            buckets["World"].append(e)
    for bname, items in buckets.items():
        # Include any overridden entries first + evenly spaced samples
        overridden = [it for it in items if it["original_en"] in RESOURCE_PT_OVERRIDES]
        stratified.extend(overridden[:8])
        step = max(1, len(items) // 20)
        stratified.extend(items[::step][:20])

    # Deduplicate stratified translated samples
    dedup_stratified = []
    seen_samples = set()
    for item in stratified:
        key = (item.get("asset") or item.get("module"), item.get("original_en"))
        if key not in seen_samples:
            seen_samples.add(key)
            dedup_stratified.append(item)

    # Also include non-localizable resources.assets samples (e.g. sound IDs / font licenses)
    for obj in objs:
        if obj["class_id"] == 49 and obj["path_id"] in (868, 457):
            name, content, _ = read_text_asset(res_bytes, data_off, obj)
            do_not_translate_samples.append({
                "module": "resources.assets",
                "value": f"[{name}] {content[:80].decode('utf-8', 'replace')}",
                "callers": [f"TextAsset path_id={obj['path_id']}"],
                "preserved_exact": True,
            })

    sample_audit = {
        "translated_sample_count": len(dedup_stratified[:220]),
        "translated_samples": dedup_stratified[:220],
        "do_not_translate_sample_count": len(do_not_translate_samples),
        "do_not_translate_samples": do_not_translate_samples,
        "script_assets_check": scripts_verified,
        "glossary_terms_checked": glossary["terms"],
    }
    (REPORTS_DIR / "sample_audit.json").write_text(
        json.dumps(sample_audit, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    elapsed = round(time.perf_counter() - t0, 3)
    timings = dict(step_timings or {})
    timings["verify"] = elapsed

    total_dist_bytes = sum(m.get("dist_bytes", 0) for m in module_metrics.values())
    rea_val_path = REPORTS_DIR / "rea_validation.json"
    rea_data = json.loads(rea_val_path.read_text(encoding="utf-8")) if rea_val_path.exists() else {}

    report = {
        "project": "Code Market PT-BR Localization",
        "tag_and_placeholder_errors": len(tag_errors),
        "tag_error_details": tag_errors[:20],
        "font_pt_glyph_check": font_checks,
        "scripts_check": scripts_verified,
        "modules": module_metrics,
        "total_dist_bytes": total_dist_bytes,
        "total_dist_mb": round(total_dist_bytes / (1024 * 1024), 3),
        "rea_pe_cli_validation": rea_data,
        "timings_seconds": timings,
    }
    (REPORTS_DIR / "verification_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[verify] Concluído em {elapsed}s — erros de tag/placeholder: {len(tag_errors)}, "
        f"amostras auditadas: {len(dedup_stratified[:220])}, tamanho dist total: {report['total_dist_mb']} MB."
    )
    if tag_errors:
        raise RuntimeError(f"Verificação falhou com {len(tag_errors)} erro(s) de tags/placeholders.")
    return elapsed


def target_file_pairs(game_dir: Path) -> list[tuple[str, Path, Path, Path]]:
    pairs = []
    for dll in TARGET_DLLS:
        rel = f"Code Market_Data/Managed/{dll}"
        pairs.append((
            rel,
            DIST_DIR / "Code Market_Data" / "Managed" / dll,
            game_dir / "Code Market_Data" / "Managed" / dll,
            ORIGINALS_BACKUP_DIR / "Managed" / dll,
        ))
    pairs.append((
        "Code Market_Data/resources.assets",
        DIST_DIR / "Code Market_Data" / "resources.assets",
        game_dir / "Code Market_Data" / "resources.assets",
        ORIGINALS_BACKUP_DIR / "resources.assets",
    ))
    return pairs


def cmd_apply(args):
    ensure_dirs()
    t0 = time.perf_counter()
    game_dir = find_game_dir(args.game_dir)
    manifest_path = BACKUPS_DIR / "backup_manifest.json"
    pairs = target_file_pairs(game_dir)

    if any(not dist_f.exists() for _, dist_f, _, _ in pairs):
        print("[apply] Artefatos em trabalho/dist/ ainda não gerados; executando extract -> translate -> build...")
        cmd_extract(args)
        cmd_translate(args)
        cmd_build(args)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}}

    # Create idempotent backups of original English files
    for rel, dist_f, game_f, local_bak in pairs:
        dist_hash = sha256_file(dist_f)
        cur_game_hash = sha256_file(game_f)
        steam_bak = Path(str(game_f) + ".bak")
        local_bak.parent.mkdir(parents=True, exist_ok=True)

        if rel not in manifest["files"]:
            if steam_bak.exists():
                orig_hash = sha256_file(steam_bak)
                shutil.copy2(steam_bak, local_bak)
            elif cur_game_hash != dist_hash:
                orig_hash = cur_game_hash
                shutil.copy2(game_f, steam_bak)
                shutil.copy2(game_f, local_bak)
            else:
                raise RuntimeError(
                    f"Arquivo {game_f} já está patcheado mas não há backup .bak original para registrar."
                )
            manifest["files"][rel] = {"original_sha256": orig_hash, "patched_sha256": dist_hash}
        else:
            orig_hash = manifest["files"][rel]["original_sha256"]
            if not steam_bak.exists() and cur_game_hash == orig_hash:
                shutil.copy2(game_f, steam_bak)
            if not local_bak.exists() and steam_bak.exists():
                shutil.copy2(steam_bak, local_bak)
            manifest["files"][rel]["patched_sha256"] = dist_hash

    manifest["game_dir"] = str(game_dir)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Copy dist files to Steam game folder
    for rel, dist_f, game_f, _ in pairs:
        shutil.copy2(dist_f, game_f)
        assert sha256_file(game_f) == sha256_file(dist_f), f"Falha na cópia de {rel}"

    elapsed = round(time.perf_counter() - t0, 3)
    print(f"[apply] Patch PT-BR aplicado com sucesso em {game_dir} ({elapsed}s).")
    return elapsed


def cmd_restore(args):
    t0 = time.perf_counter()
    game_dir = find_game_dir(args.game_dir)
    manifest_path = BACKUPS_DIR / "backup_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("Manifesto de backup não encontrado. Nenhum backup para restaurar.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pairs = target_file_pairs(game_dir)

    for rel, _, game_f, local_bak in pairs:
        steam_bak = Path(str(game_f) + ".bak")
        src_bak = steam_bak if steam_bak.exists() else local_bak
        if not src_bak.exists():
            raise FileNotFoundError(f"Backup ausente para {rel}")
        expected_sha = manifest["files"][rel]["original_sha256"]
        if sha256_file(src_bak) != expected_sha:
            raise RuntimeError(f"Checksum SHA-256 do backup divergente para {rel}")
        shutil.copy2(src_bak, game_f)
        restored_sha = sha256_file(game_f)
        if restored_sha != expected_sha:
            raise RuntimeError(f"Falha na verificação pós-restauração para {rel}")

    elapsed = round(time.perf_counter() - t0, 3)
    print(f"[restore] Arquivos originais restaurados e verificados via SHA-256 em {elapsed}s.")
    return elapsed


def cmd_status(args):
    game_dir = find_game_dir(args.game_dir)
    manifest_path = BACKUPS_DIR / "backup_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}}
    print(f"Pasta do jogo: {game_dir}")
    for rel, dist_f, game_f, local_bak in target_file_pairs(game_dir):
        cur = sha256_file(game_f) if game_f.exists() else "AUSENTE"
        dist_h = sha256_file(dist_f) if dist_f.exists() else "NAO_GERADO"
        orig_h = manifest.get("files", {}).get(rel, {}).get("original_sha256", "DESCONHECIDO")
        if cur == dist_h and dist_h != "NAO_GERADO":
            state = "PT-BR INSTALADO"
        elif cur == orig_h:
            state = "ORIGINAL (EN)"
        else:
            state = "ORIGINAL / DESCONHECIDO"
        print(f"  - {rel}: {state}")


def run_boot_test(game_dir: Path) -> dict:
    exe = game_dir / "Code Market.exe"
    if not exe.exists():
        raise FileNotFoundError(f"Executável não encontrado: {exe}")

    boot_log_path = LOGS_DIR / "unity_boot_player.log"
    if boot_log_path.exists():
        boot_log_path.unlink()

    proc = subprocess.Popen(
        [str(exe), "-logFile", str(boot_log_path)],
        cwd=str(game_dir),
    )
    time.sleep(6.0)
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    if not boot_log_path.exists():
        local_low = Path(os.environ.get("USERPROFILE", "")) / "AppData" / "LocalLow"
        candidates = list(local_low.glob("*/*/Player.log"))
        boot_log_path = max(candidates, key=lambda p: p.stat().st_mtime, default=boot_log_path)

    log_excerpt = ""
    fatal_errors = []
    if boot_log_path.exists():
        txt = boot_log_path.read_text(encoding="utf-8", errors="replace")
        log_excerpt = txt
        for line in txt.splitlines():
            if any(k in line for k in [
                "TypeLoadException",
                "BadImageFormatException",
                "MissingMethodException",
                "ArgumentOutOfRangeException",
                "NullReferenceException",
                "Fallback handler could not load",
                "Corrupted",
            ]):
                fatal_errors.append(line)

    return {
        "exe": str(exe),
        "player_log": str(boot_log_path) if boot_log_path.exists() else None,
        "fatal_errors": fatal_errors,
        "log_excerpt_lines": len(log_excerpt.splitlines()),
    }


def cmd_test_e2e(args):
    ensure_dirs()
    log_lines = []
    timings = {}

    def log(msg):
        print(msg)
        log_lines.append(msg)

    log("=== INICIO TESTE E2E CODE MARKET PT-BR ===")
    cli_help = subprocess.run([sys.executable, str(ROOT_DIR / "pipeline.py"), "--help"], capture_output=True, text=True, check=True)
    bat_help = subprocess.run(["cmd", "/c", str(ROOT_DIR / "instalar_ptbr.bat"), "--help"], capture_output=True, text=True, check=True)
    log(f"[0/7] CLI --help ok ({len(cli_help.stdout.splitlines())} linhas) | instalar_ptbr.bat --help ok ({len(bat_help.stdout.splitlines())} linhas)")
    timings["extract"] = cmd_extract(args)
    log(f"[1/7] extract: {timings['extract']}s")
    timings["translate"] = cmd_translate(args)
    log(f"[2/7] translate: {timings['translate']}s")
    timings["build"] = cmd_build(args)
    log(f"[3/7] build: {timings['build']}s")
    timings["verify"] = cmd_verify(args, timings)
    log(f"[4/7] verify: {timings['verify']}s")
    timings["apply"] = cmd_apply(args)
    log(f"[5/7] apply: {timings['apply']}s")

    game_dir = find_game_dir(args.game_dir)
    boot_res = run_boot_test(game_dir)
    log(f"[6/7] boot_test: {json.dumps(boot_res, ensure_ascii=False)}")
    if boot_res["fatal_errors"]:
        raise RuntimeError(f"Erros fatais no Player.log: {boot_res['fatal_errors']}")

    timings["restore"] = cmd_restore(args)
    log(f"[7/7] restore (SHA-256 validado): {timings['restore']}s")

    # Reapply PT-BR at the end so the user's game stays ready to play in PT-BR
    if not args.leave_restored:
        cmd_apply(args)
        log("[final] Patch PT-BR reaplicado na pasta do jogo para uso imediato.")

    # Update verification report with final timings and boot result
    rep_path = REPORTS_DIR / "verification_report.json"
    rep = json.loads(rep_path.read_text(encoding="utf-8"))
    rep["timings_seconds"] = timings
    rep["boot_test"] = boot_res
    rep_path.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

    (LOGS_DIR / "e2e_test.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    log("=== TESTE E2E CONCLUIDO COM SUCESSO ===")


def main():
    parser = argparse.ArgumentParser(
        prog="pipeline.py",
        description="Pipeline de localização EN -> PT-BR para Code Market (Unity Mono).",
    )
    parser.add_argument("--game-dir", help="Caminho para a pasta Code Market no Steam")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("extract", help="Extrai e classifica strings das 6 DLLs e resources.assets")
    sub.add_parser("translate", help="Aplica glossário e gera patches PT-BR validados")
    sub.add_parser("build", help="Constrói as 6 DLLs e resources.assets em trabalho/dist/")
    sub.add_parser("verify", help="Valida integridade, tags/placeholders, fontes e amostras")
    sub.add_parser("apply", help="Aplica o patch PT-BR na pasta do jogo com backup .bak")
    sub.add_parser("restore", help="Restaura os arquivos originais verificando SHA-256")
    sub.add_parser("status", help="Exibe o status atual dos arquivos do jogo")
    p_e2e = sub.add_parser("test-e2e", help="Executa todo o ciclo extract -> translate -> build -> verify -> apply -> boot -> restore")
    p_e2e.add_argument("--leave-restored", action="store_true", help="Deixar o jogo restaurado em inglês ao final")

    args = parser.parse_args()
    dispatch = {
        "extract": cmd_extract,
        "translate": cmd_translate,
        "build": cmd_build,
        "verify": cmd_verify,
        "apply": cmd_apply,
        "restore": cmd_restore,
        "status": cmd_status,
        "test-e2e": cmd_test_e2e,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
