#!/usr/bin/env python3
"""
Builds manifest.json for the launcher.

  python3 make_manifest.py            -> tag v<next version>
  python3 make_manifest.py v7         -> your own tag

./files/ is a copy of the GTA folder: files/modloader/Taurus/copcarsf.dff ends up in <GTA>/modloader/Taurus/copcarsf.dff
Only NEW or CHANGED files are copied into ./release/ (flat names, folders joined with "__"), the rest keeps
the link to the older release. Then it prints the exact `gh release create` command.
"""
import hashlib, json, os, re, shutil, sys

REPO = "MChkaduuu/MLauncher-Files"
OK_NAME = re.compile(r"^[A-Za-z0-9._-]+$")

manifest = {"version": 0, "files": []}
if os.path.exists("manifest.json"):
    with open("manifest.json", encoding="utf-8") as fh:
        manifest = json.load(fh)
by_path = {f["path"]: f for f in manifest["files"]}
version = int(manifest.get("version", 0)) + 1
tag = sys.argv[1] if len(sys.argv) > 1 else f"v{version}"

if not os.path.isdir("files"):
    sys.exit("No ./files folder. Create it and put the game files there (it mirrors the GTA folder).")

shutil.rmtree("release", ignore_errors=True)
os.makedirs("release")

new_assets, unchanged = [], 0
for root, _, names in os.walk("files"):
    for name in sorted(names):
        full = os.path.join(root, name)
        rel = os.path.relpath(full, "files").replace(os.sep, "/")
        if rel.startswith("..") or rel.startswith("/") or ":" in rel:
            sys.exit(f"Bad path: {rel}")
        asset = rel.replace("/", "__")
        if not OK_NAME.match(asset):
            sys.exit(f"File name not allowed for a release asset: {rel}\n"
                     "Use only letters, digits, dot, dash and underscore (no spaces).")
        h = hashlib.sha256()
        m = hashlib.md5()          # the launcher verifies files with MD5 (same as its own checks)
        with open(full, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
                m.update(chunk)
        digest = h.hexdigest()
        old = by_path.get(rel)
        if old and old["sha256"] == digest and old.get("md5"):
            unchanged += 1
            continue
        shutil.copy2(full, os.path.join("release", asset))
        new_assets.append(asset)
        by_path[rel] = {
            "path": rel,
            "url": f"https://github.com/{REPO}/releases/download/{tag}/{asset}",
            "sha256": digest,
            "md5": m.hexdigest(),
            "size": os.path.getsize(full),
        }

manifest["version"] = version
manifest["files"] = sorted(by_path.values(), key=lambda f: f["path"])
with open("manifest.json", "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2, ensure_ascii=False)

print(f"manifest.json: version {version}, {len(manifest['files'])} files "
      f"({len(new_assets)} new or changed, {unchanged} unchanged)")
if new_assets:
    print("\nCreate the release:\n")
    print(f'gh release create {tag} release/* manifest.json --title "Files {tag}" --notes "Files {tag}"')
else:
    print("\nNothing new in ./files. Only the manifest changed:\n")
    print(f'gh release create {tag} manifest.json --title "Files {tag}" --notes "Manifest {tag}"')