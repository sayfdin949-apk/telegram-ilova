"""Kurs ma'lumotlari: web/content/kurs.json, web/content/test/NN.json va server/videolar.json.

Fayllar o'zgarsa (mtime/hajm) avtomatik qayta o'qiladi - serverni qayta ishga tushirish shart emas.
Fayl yarim yozilgan bo'lsa (JSON xato), oldingi to'g'ri nusxa ishlatiladi.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import config

log = logging.getLogger("noon.kurs")
VID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


class _JsonFile:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._key = None
        self._val = None

    def get(self, default):
        try:
            st = os.stat(self.path)
        except OSError:
            return default if self._val is None else self._val
        key = (st.st_mtime_ns, st.st_size)
        if key != self._key:
            try:
                val = json.loads(self.path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError) as e:
                log.warning("JSON o'qilmadi: %s (%s)", self.path.name, e.__class__.__name__)
                return default if self._val is None else self._val
            self._key, self._val = key, val
        return self._val


class Kurs:
    def __init__(self, content_dir: Path = config.CONTENT_DIR, videolar_file: Path = config.VIDEOLAR_FILE,
                 pdf_dir: Path = config.PDF_DIR):
        self.content_dir = Path(content_dir)
        self.pdf_dir = Path(pdf_dir)
        self._kurs = _JsonFile(self.content_dir / "kurs.json")
        self._videolar = _JsonFile(Path(videolar_file))
        self._tests: dict[str, _JsonFile] = {}

    # ------------------------------------------------------------ kurs.json
    def data(self) -> dict:
        d = self._kurs.get({})
        return d if isinstance(d, dict) else {}

    def lessons(self) -> list[dict]:
        out = []
        for x in self.data().get("darslar") or []:
            if isinstance(x, dict) and isinstance(x.get("n"), int):
                out.append(x)
        return out

    def lesson(self, n) -> dict | None:
        if not isinstance(n, int) or isinstance(n, bool):
            return None
        for x in self.lessons():
            if x["n"] == n:
                return x
        return None

    def jami(self) -> int:
        d = self.data()
        j = d.get("jami_dars")
        if isinstance(j, int) and j > 0:
            return j
        ls = self.lessons()
        return max((x["n"] for x in ls), default=config.JAMI_DARS_STANDART) if ls else config.JAMI_DARS_STANDART

    def jami_slayd(self) -> int:
        j = self.data().get("jami_slayd")
        if isinstance(j, int) and j > 0:
            return j
        return sum(self.slides(x["n"]) for x in self.lessons())

    def slides(self, n: int) -> int:
        x = self.lesson(n)
        v = x.get("slaydlar") if x else None
        return v if isinstance(v, int) and v > 0 else 0

    def qismlar(self) -> list[dict]:
        q = self.data().get("qismlar") or []
        return [x for x in q if isinstance(x, dict)]

    # ------------------------------------------------------------ test/NN.json
    def _content_path(self, url: str) -> Path | None:
        """'/content/test/08.json' -> web/content/test/08.json (faqat content ichida)."""
        if not isinstance(url, str) or not url.startswith("/content/"):
            return None
        rel = url[len("/content/"):]
        if not rel or "\\" in rel or ":" in rel or "\x00" in rel:
            return None
        parts = rel.split("/")
        if any(p in ("", ".", "..") or p.startswith(".") for p in parts):
            return None
        root = self.content_dir.resolve()
        p = (root.joinpath(*parts)).resolve()
        return p if p.is_relative_to(root) else None

    def test(self, n: int) -> dict | None:
        x = self.lesson(n)
        if not x or not x.get("test"):
            return None
        p = self._content_path(x["test"])
        if p is None:
            return None
        key = str(p)
        if key not in self._tests:
            self._tests[key] = _JsonFile(p)
        t = self._tests[key].get(None)
        if not isinstance(t, dict) or not isinstance(t.get("savollar"), list) or not t["savollar"]:
            return None
        return t

    # ------------------------------------------------------------ videolar
    def video_files(self) -> list[dict]:
        v = self._videolar.get([])
        return [x for x in v if isinstance(x, dict) and isinstance(x.get("id"), str)] if isinstance(v, list) else []

    def video_path(self, vid: str) -> Path | None:
        if not isinstance(vid, str) or not VID_RE.fullmatch(vid):
            return None
        for x in self.video_files():
            if x.get("id") == vid and isinstance(x.get("fayl"), str):
                p = Path(x["fayl"])
                return p if p.is_absolute() else config.ROOT / p  # serverda: "video/d02.mp4"
        return None

    @staticmethod
    def lesson_videos(ls: dict) -> list[dict]:
        """Darsning barcha videolari: "videolar" ro'yxati (yangi), bo'lmasa eski "video" obyekti."""
        vs = ls.get("videolar")
        if isinstance(vs, list):
            return [v for v in vs if isinstance(v, dict) and isinstance(v.get("id"), str)]
        v = ls.get("video")
        return [v] if isinstance(v, dict) and isinstance(v.get("id"), str) else []

    def video_meta(self, vid: str) -> dict | None:
        """kurs.json dagi video obyekti + dars raqami: {"id","nomi","davomiylik",...,"dars"}."""
        if not isinstance(vid, str):
            return None
        for x in self.lessons():
            for v in self.lesson_videos(x):
                if v.get("id") == vid:
                    return dict(v, dars=x["n"])
        for x in self.video_files():
            if x.get("id") == vid:
                d = x.get("dars")
                return {"id": vid, "nomi": x.get("nomi"), "davomiylik": None, "dars": d if isinstance(d, int) else None}
        return None

    def lesson_of_video(self, vid: str) -> int | None:
        m = self.video_meta(vid)
        return m.get("dars") if m else None

    # ------------------------------------------------------------ PDF
    def pdf_path(self, n: int) -> Path | None:
        x = self.lesson(n)
        name = x.get("pdf") if x else None
        if not isinstance(name, str) or not name or "/" in name or "\\" in name or ":" in name or name.startswith("."):
            return None
        root = self.pdf_dir.resolve()
        p = (root / name).resolve()
        if not p.is_relative_to(root) or not p.is_file():
            return None
        return p
