#!/usr/bin/env python
"""Fast-path OCR ingestion for large scanned textbooks."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from urllib import error, parse, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Import large scanned textbooks with a faster workflow: "
            "skip irrelevant files, prefilter likely blank pages, cache OCR output, "
            "upload only useful pages, then auto-generate cards."
        )
    )
    parser.add_argument("input_path", help="Path to one PDF file or a directory of PDFs")
    parser.add_argument("--collection-id", type=int, required=True, help="Target collection ID")
    parser.add_argument(
        "--api-base",
        default="https://iroli1.online",
        help="OCDOCTOR API base URL",
    )
    parser.add_argument(
        "--subject-key",
        default="acupuncture",
        choices=("acupuncture", "warm_disease"),
        help="Subject key used for page relevance and template selection",
    )
    parser.add_argument(
        "--render-scale",
        type=float,
        default=1.0,
        help="Page render scale used for OCR",
    )
    parser.add_argument(
        "--glob",
        default="*.pdf",
        help="Glob pattern when input_path is a directory",
    )
    parser.add_argument(
        "--cache-dir",
        default=".cache/priority-ocr",
        help="Directory for OCR cache JSON files",
    )
    parser.add_argument(
        "--min-char-count",
        type=int,
        default=90,
        help="Minimum OCR chars for a page without strong keywords",
    )
    parser.add_argument(
        "--blank-dark-ratio",
        type=float,
        default=0.008,
        help="Skip pages whose dark-pixel ratio is below this threshold",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Only process files whose names match this regex. Can be repeated.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Skip files whose names match this regex. Can be repeated.",
    )
    parser.add_argument(
        "--auto-generate",
        action="store_true",
        help="Generate cards automatically after each document is imported",
    )
    parser.add_argument(
        "--templates",
        action="append",
        default=[],
        help="Explicit template key(s) to generate. Can be repeated.",
    )
    parser.add_argument(
        "--skip-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip PDFs whose file names already exist in the target collection",
    )
    return parser


def main() -> int:
    """Run the fast-path OCR ingestion flow."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        import fitz
        from PIL import Image
        from tcm_study_app.services.ocr_service import OCRService
    except ModuleNotFoundError as exc:
        parser.exit(1, f"Missing dependency: {exc.name}\n")

    ocr_service = OCRService()
    if not ocr_service.is_available():
        parser.exit(1, f"{ocr_service.get_installation_hint()}\n")

    input_path = Path(args.input_path).expanduser()
    pdf_files = _resolve_pdf_files(input_path, args.glob)
    pdf_files = [
        path
        for path in pdf_files
        if _matches_file_filters(path.name, args.include, args.exclude)
    ]
    api_base = args.api_base.rstrip("/")
    cache_root = Path(args.cache_dir).expanduser()
    cache_root.mkdir(parents=True, exist_ok=True)

    existing_names = (
        _fetch_existing_document_names(api_base, args.collection_id)
        if args.skip_existing
        else set()
    )
    imported_count = 0

    for pdf_path in pdf_files:
        if args.skip_existing and pdf_path.name in existing_names:
            print(f"跳过已存在文档: {pdf_path.name}")
            continue

        suggested_templates = args.templates or _suggest_templates(
            pdf_path.name,
            args.subject_key,
        )
        if not suggested_templates:
            print(f"跳过低价值文档: {pdf_path.name}")
            continue

        cache_path = _cache_path_for_pdf(cache_root, pdf_path)
        if cache_path.exists():
            pages = json.loads(cache_path.read_text(encoding="utf-8"))
            print(f"使用 OCR 缓存: {pdf_path.name} ({len(pages)} 页)")
        else:
            pages = _extract_relevant_pages(
                pdf_path,
                ocr_service=ocr_service,
                fitz_module=fitz,
                image_module=Image,
                subject_key=args.subject_key,
                render_scale=args.render_scale,
                min_char_count=args.min_char_count,
                blank_dark_ratio=args.blank_dark_ratio,
            )
            cache_path.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
            print(f"完成 OCR 预处理: {pdf_path.name} ({len(pages)} 页保留)")

        if not pages:
            print(f"没有保留页面，跳过上传: {pdf_path.name}")
            continue

        payload = {
            "collection_id": args.collection_id,
            "file_name": pdf_path.name,
            "pages": pages,
        }
        response = _post_json(f"{api_base}/api/import/ocr-pages", payload)
        imported_count += 1
        print(
            f"已导入 {pdf_path.name}: "
            f"document_id={response['document_id']} "
            f"page_count={response['page_count']} "
            f"chunk_count={response['chunk_count']}"
        )

        if args.auto_generate:
            for template_key in suggested_templates:
                try:
                    generation = _post_json(
                        f"{api_base}/api/cards/generate?user_id=1",
                        {
                            "document_id": response["document_id"],
                            "template_key": template_key,
                        },
                    )
                    print(
                        f"  生成模板 {template_key}: {len(generation.get('cards', []))} 张卡"
                    )
                except SystemExit as exc:
                    print(f"  模板 {template_key} 跳过: {exc}")

    print(f"完成，共导入 {imported_count} 个 PDF。")
    return 0


def _resolve_pdf_files(input_path: Path, pattern: str) -> list[Path]:
    """Resolve one PDF or a sorted PDF list from a directory."""
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        pdf_files = sorted(path for path in input_path.glob(pattern) if path.is_file())
        if not pdf_files:
            raise SystemExit(f"目录里没有匹配到 PDF: {input_path}")
        return pdf_files
    raise SystemExit(f"找不到输入路径: {input_path}")


def _matches_file_filters(file_name: str, include: list[str], exclude: list[str]) -> bool:
    """Apply include/exclude regex filters to the file name."""
    if include and not any(re.search(pattern, file_name) for pattern in include):
        return False
    if any(re.search(pattern, file_name) for pattern in exclude):
        return False
    return True


def _cache_path_for_pdf(cache_root: Path, pdf_path: Path) -> Path:
    """Build a stable OCR cache path for one PDF."""
    stat = pdf_path.stat()
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", pdf_path.stem).strip("._") or "document"
    return cache_root / f"{safe_name}_{stat.st_size}_{stat.st_mtime_ns}.json"


def _fetch_existing_document_names(api_base: str, collection_id: int) -> set[str]:
    """Fetch existing document names in the target collection."""
    query = parse.urlencode({"collection_id": collection_id})
    payload = _get_json(f"{api_base}/api/documents?{query}")
    return {item.get("file_name", "") for item in payload if item.get("file_name")}


def _suggest_templates(file_name: str, subject_key: str) -> list[str]:
    """Map a split-PDF file name to the most likely useful templates."""
    if subject_key == "acupuncture":
        if re.search(r"经络腧穴各论|手太阴肺经|手阳明大肠经|腧穴", file_name):
            return ["acupoint_foundation", "acupoint_review"]
        if re.search(
            r"针灸临床诊治思维|治疗总论|病症|病证|疼症|心脑病症|肺系病症|肝胆脾胃病症|肾膀胱病症|气血津液病症|皮肤外科病症|妇儿科病症|五官病症|其他病症",
            file_name,
        ):
            return ["clinical_treatment"]
        return []

    if subject_key == "warm_disease":
        if re.search(r"总论|辨证|风温|湿温|春温|暑温|温病", file_name):
            return ["pattern_treatment", "pattern_stage_review"]
    return []


def _extract_relevant_pages(
    pdf_path: Path,
    *,
    ocr_service,
    fitz_module,
    image_module,
    subject_key: str,
    render_scale: float,
    min_char_count: int,
    blank_dark_ratio: float,
) -> list[dict[str, object]]:
    """OCR only pages that look non-blank and keep pages likely to be useful."""
    document = fitz_module.open(str(pdf_path))
    kept_pages: list[dict[str, object]] = []

    with TemporaryDirectory(prefix="ocdoctor-priority-ocr-") as temp_dir:
        temp_root = Path(temp_dir)
        for page_number in range(1, len(document) + 1):
            page = document.load_page(page_number - 1)
            if _is_probably_blank_page(
                page,
                fitz_module=fitz_module,
                dark_ratio_threshold=blank_dark_ratio,
            ):
                continue

            pixmap = page.get_pixmap(
                matrix=fitz_module.Matrix(render_scale, render_scale),
                alpha=False,
            )
            image_path = temp_root / f"page_{page_number:04d}.png"
            pixmap.save(image_path)
            text = ocr_service.extract_text_from_image(str(image_path)).strip()
            if not _is_relevant_page_text(
                text,
                subject_key=subject_key,
                file_name=pdf_path.name,
                min_char_count=min_char_count,
            ):
                continue
            kept_pages.append({"page_number": page_number, "text": text})

    return kept_pages


def _is_probably_blank_page(page, *, fitz_module, dark_ratio_threshold: float) -> bool:
    """Use a cheap render to skip nearly blank pages before OCR."""
    pixmap = page.get_pixmap(matrix=fitz_module.Matrix(0.25, 0.25), alpha=False)
    data = memoryview(pixmap.samples)
    dark_pixels = 0
    pixel_count = pixmap.width * pixmap.height
    for index in range(0, len(data), pixmap.n):
        rgb = data[index : index + 3]
        if (rgb[0] + rgb[1] + rgb[2]) / 3 < 245:
            dark_pixels += 1
    return pixel_count == 0 or (dark_pixels / pixel_count) < dark_ratio_threshold


def _is_relevant_page_text(
    text: str,
    *,
    subject_key: str,
    file_name: str,
    min_char_count: int,
) -> bool:
    """Keep pages likely to help card generation and drop obvious noise."""
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return False

    if subject_key == "acupuncture":
        if "clinical_treatment" in " ".join(_suggest_templates(file_name, subject_key)):
            treatment_keywords = (
                "治法",
                "治则",
                "处方",
                "取穴",
                "主穴",
                "配穴",
                "治疗方案",
                "治疗策略",
                "基本处方",
                "针灸处方",
            )
            disease_keywords = (
                "病",
                "症",
                "综合征",
                "痹",
                "痛",
                "瘫",
                "哮",
                "痫",
                "聋",
                "闭经",
                "带下",
                "遗尿",
                "泄泻",
            )
            noise_keywords = (
                "目录",
                "编写说明",
                "前言",
                "参考文献",
                "版权页",
                "检查要点",
                "预后",
                "难点分析",
                "解决思路",
                "病因病机",
                "病因辨证",
                "按辨证",
                "共同症",
                "兼症",
                "方义",
            )
            has_treatment = any(keyword in compact for keyword in treatment_keywords)
            has_disease = any(keyword in compact for keyword in disease_keywords)
            if any(keyword in compact for keyword in noise_keywords) and not has_treatment:
                return False
            if has_treatment and has_disease:
                return True
            return len(compact) >= max(min_char_count, 220) and has_treatment
        else:
            strong_keywords = (
                "定位",
                "主治",
                "操作",
                "刺灸法",
                "经穴",
                "腧穴",
                "原穴",
                "络穴",
            )
    else:
        strong_keywords = ("证候", "治法", "方药", "辨证", "卫分", "气分", "营分", "血分")

    noise_keywords = ("目录", "编写说明", "前言", "参考文献", "版权页")
    if any(keyword in compact for keyword in strong_keywords):
        return True
    if any(keyword in compact for keyword in noise_keywords):
        return False
    return len(compact) >= min_char_count


def _get_json(url: str):
    """GET JSON and return the decoded response."""
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"请求失败 {exc.code}: {detail}") from exc


def _post_json(url: str, payload: dict) -> dict:
    """POST JSON and return the decoded response."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"上传失败 {exc.code}: {detail}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
