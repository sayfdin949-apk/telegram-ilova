# 8-dars taqdimotining 5-slaydidagi rasmni (og'iz bo'shlig'i sxemasi) aynan nusxa qilib oladi.
# Manba faqat o'qiladi: web\content\taqdimot\4\index.html
import re
from pathlib import Path

SRC = Path(r"C:\Users\N.M\Desktop\MUHAMMAD AMIN\Telegram ilova\web\content\taqdimot\4\index.html")
OUT = Path(__file__).with_name("slayd05_rasm.txt")

html = SRC.read_text(encoding="utf-8")
start = html.index("<!-- 05 -->")
end = html.index("<!-- 06 -->")
block = html[start:end]
m = re.search(r'<span class="qpic"><img[^>]*src="(data:[^"]+)"', block)
uri = m.group(1)
OUT.write_text(uri, encoding="utf-8")
print("turi:", uri[:40], "| hajmi:", round(len(uri) / 1024), "KB")
