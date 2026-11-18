# 部署到 GitHub Pages（在你的笔记本上执行，共 4 步）

本机（HPC）到 GitHub 网络不通，所以整个仓库已打包好：
`/public/home/sjl2/envtoldb_site/envtoldb_site.tar.gz` —— 拷到笔记本后：

## 1. 解压并进入仓库

```bash
tar xzf envtoldb_site.tar.gz && cd envtoldb_site
```

## 2. 在 GitHub 上创建空仓库

登录 GitHub → New repository → 命名 `envtoldb`（建议 Public）→ **不要**勾选任何初始化文件 → Create。

## 3. 推送（首次约 300–500MB，耐心等）

```bash
git push -u origin main
```

## 4. 开启 Pages

GitHub 网页 → Settings → Pages → Source 选 **GitHub Actions** → 到 Actions 页确认
"Deploy EnvTolDB to GitHub Pages" 跑完 → 访问 `https://<用户名>.github.io/envtoldb/`

## 以后更新数据

HPC 上重新生成站点并刷新打包：

```bash
python3 /public/home/sjl2/envtoldb_site/build_static_site.py
cd /public/home/sjl2/envtoldb_site && git add -A && git commit -m "data update $(date +%F)" && tar czf envtoldb_site.tar.gz envtoldb_site
```

再拷到笔记本 push 即可（Actions 会自动重新部署）。

## 注意

- 仓库约 500MB（含整库 SQLite.gz + 231 个 FASTA.gz），clone 建议加 `--depth 1`
- 单文件均 <100MB（GitHub 硬限制以内）；db.gz 若将来超 100MB 需改放到 Releases
