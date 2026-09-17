"""临时验收：博客收录修复（sitemap 全量 / 归档取数 / robots 指向 / 部署脚本语法）
范围：改动行为断言，非套件测试。构建输出到临时目录，不污染工作区。
"""
import os, re, subprocess, sys, tempfile, glob
import xml.etree.ElementTree as ET

SITE = r"D:\blog-work"
fails, checks = [], []

def chk(name, ok, detail=""):
    checks.append((name, ok, detail))
    if not ok:
        fails.append(name)

# 0) 部署脚本语法
GIT_BASH = r"D:\Program Files\Git\usr\bin\bash.exe"   # 注意: 直接调 "bash" 会命中 WSL bash
r = subprocess.run([GIT_BASH, "-n", "/c/Users/zjjem/AppData/Local/Temp/deploy_blog.sh"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
chk("deploy_blog.sh 语法 (bash -n)", r.returncode == 0, (r.stderr or "").strip()[:200])

# 1) 从源码重建到临时目录（不碰仓库 public/）
out = tempfile.mkdtemp(prefix="hermes-verify-blog-")
r = subprocess.run(["hugo", "--gc", "--minify", "-d", out], cwd=SITE,
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
chk("hugo 构建成功", r.returncode == 0, (r.stderr or r.stdout).strip()[-200:])

posts = glob.glob(os.path.join(SITE, "content", "posts", "*.md"))
n_posts = len(posts)

# 2) sitemap：全量 + 无重复 + 含首页
sm = os.path.join(out, "sitemap.xml")
chk("sitemap.xml 生成", os.path.exists(sm))
x = open(sm, encoding="utf-8").read()
root = ET.fromstring(x)                                   # 格式非法会抛异常
ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
locs = [e.text for e in root.iter(ns + "loc")]
art = [l for l in locs if re.search(r"/20\d\d/\d\d/", l)]
chk(f"sitemap XML 合法且文章页 = {n_posts}", len(art) == n_posts, f"实际 {len(art)}")
chk("sitemap 无重复 <loc>", len(locs) == len(set(locs)),
    f"{len(locs)} 条 / 去重 {len(set(locs))}")
chk("sitemap 含首页", "https://zhengjinjun1975.github.io/" in locs)
chk("sitemap 含栏目页 /posts/", "https://zhengjinjun1975.github.io/posts/" in locs)

# 3) 归档页：列全文章（修复前恒为 0）
ah = open(os.path.join(out, "archives", "index.html"), encoding="utf-8").read()
n_arch = len(re.findall(r'class="?archive-item', ah))
chk(f"归档页条目 = {n_posts}", n_arch == n_posts, f"实际 {n_arch}")

# 4) 文章列表页：列全文章
ph = open(os.path.join(out, "posts", "index.html"), encoding="utf-8").read()
n_cards = len(re.findall(r'class="?post-card(?:\s|>|")', ph))
chk(f"列表页文章卡片 = {n_posts}", n_cards == n_posts, f"实际 {n_cards}")

# 5) robots.txt 指向 sitemap（baseURL 来源一致性）
rb = open(os.path.join(out, "robots.txt"), encoding="utf-8").read()
base = re.search(r'baseURL\s*=\s*"([^"]+)"', open(os.path.join(SITE, "hugo.toml"), encoding="utf-8").read()).group(1)
chk("robots.txt Sitemap 指向 baseURL", f"Sitemap: {base}sitemap.xml" in rb,
    re.search(r"Sitemap: .*", rb).group(0) if "Sitemap" in rb else "缺 Sitemap 行")

# 6) front matter 引号污染回归（tags/categories 不得含中文引号）
bad = []
for f in posts:
    fm = open(f, encoding="utf-8").read().split("---")[1] if "---" in open(f, encoding="utf-8").read() else ""
    for line in fm.splitlines():
        if line.startswith(("tags:", "categories:")) and ("\u201c" in line or "\u201d" in line):
            bad.append(os.path.basename(f))
chk("front matter tags/categories 无中文引号", not bad, str(bad))

print(f"构建输出: {out}\n")
for name, ok, detail in checks:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
print(f"\n{len(checks) - len(fails)}/{len(checks)} 通过")
sys.exit(1 if fails else 0)
