# 护花使者门户网站 · 协作与发布指南

> 这份文档既给人看，也给 AI 助手看。照做即可安全地修改并发布网站。

## 1. 基本信息

| 项目 | 内容 |
|---|---|
| 线上地址 | https://yaoshuai01.github.io/huhuashizhe-portal/ |
| 门户仓库 | https://github.com/YaoShuai01/huhuashizhe-portal （本仓库） |
| 主项目仓库 | https://github.com/YaoShuai01/huhuashizhe |
| 发布方式 | GitHub Pages，直接发布 `main` 分支根目录，无构建步骤 |
| 技术栈 | 单个 `index.html`（内联 CSS/JS）+ `assets/` 静态资源 |

主项目仓库通过 **git submodule** 引用本仓库，路径为 `portal/`。本仓库的提交才是网站的真实内容；主仓库只记录一个指向本仓库的 commit 指针。

## 2. 目录结构

```text
portal/
├── index.html          # 主站：结构 + 样式 + 交互，全部在这一个文件里
├── quadcopter.html     # 子项目：四旋翼三维拆解工作台（内联 three.js）
├── 404.html            # 品牌化 404 页，GitHub Pages 自动接管
├── robots.txt          # 抓取规则，指向 sitemap
├── sitemap.xml         # 两个页面的站点地图
├── .nojekyll           # 关闭 GitHub Pages 的 Jekyll 处理，不要删
├── README.md           # 本文档
├── tools/
│   ├── check_versions.py    # 发布前校验：版本号 / APK 名 / 本地资源 / sha256 断言
│   └── build_singlefile.py  # 生成单文件版并打包 无人机官网.zip
└── assets/
    └── img/            # 所有图片，jpg/webp/png
```

## 3. 修改与发布流程

### 3.1 只改网站（推荐路径）

```bash
git clone https://github.com/YaoShuai01/huhuashizhe-portal.git
cd huhuashizhe-portal
git pull

# 本地预览（不需要任何构建工具）
python -m http.server 8000
# 浏览器打开 http://localhost:8000

# 修改 index.html 或 assets/img
git add .
git commit -m "update: 简要说明改了什么"
git push origin main
```

推送到 `main` 后 1~2 分钟，GitHub Pages 会自动更新线上站点。

### 3.2 从主项目仓库协作（含子模块）

```bash
git clone --recurse-submodules https://github.com/YaoShuai01/huhuashizhe.git
# 已有仓库时：
git submodule update --init --recursive
```

修改并发布网站：

```bash
cd portal
git pull
# 改网站
git add .
git commit -m "update: 简要说明改了什么"
git push origin main

cd ..
git add portal          # 更新主仓库里的子模块指针
git commit -m "chore: 更新门户子模块"
git push
```

> 关键：如果只 push 了门户仓库、没有在主仓库更新 `portal` 指针，合作者拉主仓库时看到的仍是旧网站。

合作者同步网站：

```bash
git pull
git submodule update --remote portal
```

## 4. 给 AI 助手的硬性规则

修改本网站时，必须遵守以下约束：

1. **不引入构建工具**：禁止 npm/vite/webpack/React/Tailwind 等。网站必须保持“打开 `index.html` 就能看、push 就能发布”。
2. **保持单文件结构**：样式写在 `<style>`，脚本写在 `<script>`，不要拆成多个 CSS/JS 文件，除非用户明确要求。
3. **沿用现有设计系统**：颜色只用 `:root` 里已有的变量（`--green`、`--green-deep`、`--lime`、`--amber`、`--bg`、`--ink`、`--muted` 等）；字体只用 `--font-display`、`--font-serif`、`--font-mono`。不要引入新的视觉风格。
4. **不重排无关代码**：只改需求涉及的部分，不要顺手格式化整个文件、不要改无关 section 的顺序。
5. **中文文案**：保持现有语气，简洁、具体、不堆形容词，不写空泛的营销口号。
6. **响应式必须成立**：改完至少检查 375px（手机）、768px（平板）、1440px（桌面）三档，不允许出现横向滚动、文字溢出、按钮重叠。
7. **可访问性**：图片必须有 `alt`；交互元素用 `<a>` / `<button>`；保留 `aria-*` 属性；不要用纯颜色表达状态。
8. **图片规范**：
   - 新图片放 `assets/img/`，文件名用小写英文 + 连字符，例如 `field-scan.jpg`。
   - 优先同时提供 `.webp` 和 `.jpg` 两份，用 `<picture>` 或 `srcset` 引用，保持现有写法。
   - 单张图控制在 300KB 以内；不要提交未使用的图片。
   - `og:image` 必须使用线上绝对地址。
9. **链接规范**：下载链接、二维码、版本号会在多处重复出现（`<head>` 的 JSON-LD、导航、Hero、下载卡片）。改版本号时用搜索替换全部同步。
10. **禁止提交**：`node_modules`、构建产物、编辑器缓存、密钥、`.env`、系统缩略图文件。
11. **提交信息**：`update: ...` / `fix: ...` / `feat: ...`，一句话说明改动目的，不要用“修改”两个字敷衍。
12. **发布前必须自检**（见第 6 节），自检不通过不允许 push。

## 5. 常见修改示例

### 改文案

直接改 `index.html` 中对应文本。注意同步 `<title>`、`meta description`、`og:description` 和 JSON-LD 里的描述，避免搜索结果与页面不一致。

### 改 App 下载版本

当前版本号（例如 `v3.10.13`）在 `index.html` 里硬编码 15 处、APK 文件名 8 处，全部要一起替换。**改完必须跑校验脚本，不要只靠肉眼搜索**：

```bash
python tools/check_versions.py --apk /path/to/huhuashizhe_v3.10.13.apk
```

脚本会断言：版本号只有一种、APK 文件名与页面版本一致、页面引用的本地资源都存在、公示的 sha256 与 APK 实际值一致。任意一项失败即退出码 1，不允许 push。

同一支脚本已挂进 CI（`.github/workflows/verify.yml`）：push / PR 到 `main` 时自动执行并顺带探测下载源可达性，断言失败直接标红，不再依赖人肉自检。

涉及位置通常包括：JSON-LD 的 `softwareVersion` / `downloadUrl` / `sha256`、导航按钮、Hero 按钮、两张下载卡片、移动菜单、底部下载条。

### 新增一个板块

1. 在 `<main>` 内、合适的 section 之后插入 `<section class="section" id="新id" aria-labelledby="新id-h">`。
2. 沿用现有 `.section__head`、`.kicker`、`h2`、`data-reveal` 等结构。
3. 如果导航需要入口，同步改 `<nav class="nav__links">` 和移动菜单。
4. 新样式只加在现有 `<style>` 末尾，使用已有变量，不要覆盖全局选择器。

### 换图片

替换 `assets/img/` 下的文件，保持文件名不变时无需改 HTML；新增文件名时要同步修改 HTML 引用和 `srcset` 宽度描述。

## 6. 发布前自检清单

- [ ] `python -m http.server` 本地打开无白屏
- [ ] 浏览器控制台无报错
- [ ] 375px / 768px / 1440px 三档无横向滚动、无重叠
- [ ] 所有图片能加载，`alt` 不为空
- [ ] 所有站内锚点可跳转，所有外链可打开
- [ ] 下载按钮指向的 APK 链接真实存在
- [ ] 版本号、APK 文件名在全文已同步（`python tools/check_versions.py --apk <apk路径>` 全绿）
- [ ] 页面公示的 sha256 与 APK 实际值一致（同一支脚本断言）
- [ ] 页面标题、描述、`og:image` 正确
- [ ] `git status` 中没有误加的临时文件
- [ ] `git diff` 只包含本次需求相关改动

## 7. 发布后验证

1. 打开 https://yaoshuai01.github.io/huhuashizhe-portal/
2. 强制刷新（Ctrl+F5）或手机无痕模式打开，避免 CDN 缓存
3. 检查：首屏图片、导航、下载按钮、页脚链接
4. 如果 5 分钟后仍未更新，去 GitHub 仓库的 **Actions / Pages** 页面查看部署状态

## 8. 可直接粘贴给 AI 的提示词模板

```text
你在维护护花使者门户网站仓库：
https://github.com/YaoShuai01/huhuashizhe-portal

要求：
1. 网站是单文件 index.html + assets/img，无构建步骤，直接 GitHub Pages 发布 main 分支。
2. 只改我指定的内容，不要重构、不要格式化无关代码、不要引入任何依赖。
3. 沿用现有 CSS 变量和设计风格，保持响应式与可访问性。
4. 改完先本地 python -m http.server 预览，按 README 第 6 节自检。
5. 自检通过后 commit 并 push 到 main；如果是通过主仓库的子模块工作，还要在主仓库更新 portal 指针并提交。

本次需求：<在这里写清楚要改什么>
```

## 9. 权限

- 能直接 push 的合作者：需要在门户仓库 Settings → Collaborators 中被添加为协作者（Write 权限）。
- 没有写权限：Fork 后提 Pull Request，由维护者合并。
- 如果 `main` 开了分支保护：不要强推，走 PR 流程。

## 10. 绝对不要做的事

- 不要删除 `.nojekyll`（会导致 Pages 处理异常）。
- 不要把 `portal` 作为普通目录再提交进主仓库（它已经是子模块）。
- 不要在门户仓库里提交主项目的固件、APK 构建产物或训练数据。
- 不要为了“优化”把单文件拆成框架工程。
- 不要提交未使用的图片或超过 300KB 的单图。
