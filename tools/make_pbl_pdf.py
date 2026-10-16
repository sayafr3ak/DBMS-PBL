"""Prints docs/PBL_Report.html to docs/PBL_Report_Arjun_Pal.pdf with headless Microsoft Edge.

    python tools/make_pbl_pdf.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "docs", "PBL_Report.html")
PDF = os.path.join(ROOT, "docs", "PBL_Report_Arjun_Pal.pdf")
EDGE = next(p for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"] if os.path.exists(p))


def build():
    for attempt in range(4):
        if os.path.exists(PDF):
            os.remove(PDF)
        profile = tempfile.mkdtemp(prefix="edge-pdf-")          # fresh profile: avoids lock clashes
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", f"--user-data-dir={profile}", "--no-pdf-header-footer",
                        f"--print-to-pdf={PDF}", "--virtual-time-budget=6000", "file:///" + HTML.replace("\\", "/")],
                       capture_output=True, timeout=120)
        for _ in range(40):                                       # Edge can return before the file is flushed
            if os.path.exists(PDF) and os.path.getsize(PDF) > 0:
                break
            time.sleep(0.5)
        shutil.rmtree(profile, ignore_errors=True)
        if os.path.exists(PDF):
            return True
    return False


if __name__ == "__main__":
    if not build():
        sys.exit("PDF was not created")
    try:
        import pymupdf
        doc = pymupdf.open(PDF)
        print(f"pages: {len(doc)}")
        for i, page in enumerate(doc):
            lines = [x for x in page.get_text().split("\n") if x.strip()]
            print(f"{i + 1:>2} | {(lines[1] if len(lines) > 1 else '')[:55]} | lines {len(lines)}")
    except ImportError:
        print("PDF created:", PDF)
