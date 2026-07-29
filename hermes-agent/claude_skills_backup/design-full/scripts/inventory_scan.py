"""
inventory_scan.py <root>

Walk the project tree and emit a JSON inventory of style files, framework,
planning files, and entry screens.  Stdlib-only, ASCII-safe, exit-0 always.

Called by design-full/SKILL.md P1 AUDIT step:
    python <skill>/scripts/inventory_scan.py <project-root>
Output fields: root, style_files, framework, planning_files, entry_screens, counts.
"""

import json
import os
import sys
import re

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt",
    "vendor", "__pycache__", ".worktrees", "exclude", ".design-full",
}

STYLE_EXTS = {
    ".scss": "scss",
    ".sass": "scss",
    ".css": "css",
    ".less": "less",
    ".styl": "stylus",
    ".stylus": "stylus",
}

ROADMAP_RE = re.compile(r"roadmap", re.IGNORECASE)

ENTRY_PATTERNS = {
    "src/App.tsx", "src/App.jsx", "src/App.js", "src/App.ts",
    "src/main.tsx", "src/main.jsx", "src/main.js", "src/main.ts",
    "pages/index.tsx", "pages/index.jsx", "pages/index.js",
    "app/page.tsx", "app/page.jsx", "app/page.js",
    "index.html",
    "lib/main.dart",
}


def classify_style_file(rel_path, pkg_deps):
    """Return (kind, rel_path) or None if not a style file."""
    low = rel_path.lower()
    basename = os.path.basename(low)

    # tailwind config
    if basename in (
        "tailwind.config.js", "tailwind.config.ts",
        "tailwind.config.mjs", "tailwind.config.cjs",
    ):
        return "tailwind-config"

    # theme / token files by name
    if any(kw in basename for kw in ("theme", "token", "tokens")):
        ext = os.path.splitext(basename)[1]
        if ext in (".js", ".ts", ".json", ".scss", ".css"):
            return "tokens" if "token" in basename else "theme"

    # css-in-js: .styled.* filenames
    if ".styled." in low:
        return "css-in-js"

    # css-in-js from styled-components dep + .tsx containing "styled."
    # We check only filenames here (no code parse); dep check done in detect_framework
    ext = os.path.splitext(basename)[1]
    if ext in STYLE_EXTS:
        return STYLE_EXTS[ext]

    return None


def read_package_json(root):
    """Return (all_dep_names: set, raw_dict) for package.json at root."""
    pkg_path = os.path.join(root, "package.json")
    if not os.path.isfile(pkg_path):
        return set(), {}
    try:
        with open(pkg_path, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
        deps = set()
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            if isinstance(data.get(section), dict):
                deps.update(data[section].keys())
        return deps, data
    except Exception:
        return set(), {}


def detect_framework(root, pkg_deps):
    """Return {"name": ..., "evidence": [...]}."""
    name = "unknown"
    evidence = []

    # pubspec.yaml -> flutter
    if os.path.isfile(os.path.join(root, "pubspec.yaml")):
        name = "flutter"
        evidence.append("pubspec.yaml present")
        return {"name": name, "evidence": evidence}

    # package.json dep-based detection (order matters: more-specific first)
    dep_map = [
        ("expo", "react-native"),
        ("react-native", "react-native"),
        ("@angular/core", "angular"),
        ("nuxt", "nuxt"),
        ("next", "next"),
        ("svelte", "svelte"),
        ("vue", "vue"),
        ("react", "react"),
    ]
    for dep, fw in dep_map:
        if dep in pkg_deps:
            name = fw
            evidence.append("package.json dep " + dep)
            return {"name": name, "evidence": evidence}

    # file-extension fallback
    for ext_check in (".tsx", ".jsx"):
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if f.endswith(ext_check):
                    name = "react"
                    evidence.append("file extension " + ext_check)
                    return {"name": name, "evidence": evidence}
            break  # only top-level scan for speed; full walk below

    # if .vue files exist
    for _dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith(".vue"):
                name = "vue"
                evidence.append("file extension .vue")
                return {"name": name, "evidence": evidence}

    if evidence:
        return {"name": name, "evidence": evidence}
    return {"name": "plain", "evidence": ["no known framework detected"]}


def is_planning_file(rel_path):
    """True if the path looks like a TODO/roadmap planning file."""
    parts = rel_path.replace("\\", "/").split("/")
    basename = os.path.basename(rel_path).lower()
    depth = len(parts) - 1  # number of directories above the file

    if depth > 3:
        return False

    if basename in ("todo.md", "todo.txt"):
        return True

    # any directory named "todo" (case-insensitive)
    for part in parts[:-1]:
        if part.lower() == "todo":
            return True

    if ROADMAP_RE.search(basename):
        return True

    return False


def is_entry_screen(rel_path):
    """True if matches known entry patterns (forward-slash normalised)."""
    norm = rel_path.replace("\\", "/")
    return norm in ENTRY_PATTERNS


def scan(root):
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        return {"error": "not a directory: " + root}

    pkg_deps, _pkg_data = read_package_json(root)

    # check styled-components dep for css-in-js classification
    has_styled_components = "styled-components" in pkg_deps or "@emotion/styled" in pkg_deps

    style_files = []
    planning_files = []
    entry_screens = []
    files_scanned = 0

    for dirpath, dirs, files in os.walk(root, topdown=True):
        # prune skip dirs in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for fname in files:
            files_scanned += 1
            abs_path = os.path.join(dirpath, fname)
            try:
                rel_path = os.path.relpath(abs_path, root).replace("\\", "/")
            except ValueError:
                continue

            # planning files
            if is_planning_file(rel_path):
                planning_files.append(rel_path)
                continue

            # entry screens
            if is_entry_screen(rel_path):
                entry_screens.append(rel_path)

            # style files
            kind = classify_style_file(rel_path, pkg_deps)
            if kind is None and has_styled_components:
                # cheap heuristic: .tsx files with "styled." in name
                if fname.endswith(".tsx") and "styled" in fname.lower():
                    kind = "css-in-js"

            if kind is not None:
                try:
                    byte_size = os.path.getsize(abs_path)
                except OSError:
                    byte_size = 0
                style_files.append({
                    "path": rel_path,
                    "kind": kind,
                    "bytes": byte_size,
                })

    framework = detect_framework(root, pkg_deps)

    return {
        "root": root,
        "style_files": style_files,
        "framework": framework,
        "planning_files": sorted(set(planning_files)),
        "entry_screens": sorted(set(entry_screens)),
        "counts": {
            "files_scanned": files_scanned,
            "style_files": len(style_files),
        },
    }


def main():
    try:
        root = sys.argv[1] if len(sys.argv) > 1 else ""
        if not root:
            print(json.dumps({"error": "usage: inventory_scan.py <root>"}))
            return
        result = scan(root)
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))


if __name__ == "__main__":
    main()
