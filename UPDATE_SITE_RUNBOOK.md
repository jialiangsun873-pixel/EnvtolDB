# EnvtolDB 网站自动更新运行手册 (2026-11-24, 配合定时监控任务)

目的: IPG 映射 (gene-ipg-map.service) 完成后, 自动完成 EBI 补跑 → 坐标导入 → 站点重建 → 推送 GitHub Pages。
范围 (用户已确认): NCBI + EBI 即更新; CDS 阶段不在本轮。

## 完成判定 (Step 0)
ssh sjl2 检查 (免密, Git 客户端 /usr/bin/ssh 或 Git for Windows 均可):
  python3 -c "import sqlite3;db=sqlite3.connect('/public/home/sjl2/datasetdb/gene_seqs/full_gene/full_mapping/ipg_mapping.sqlite');print(dict(db.execute('SELECT status,COUNT(*) FROM targets GROUP BY status')))"
完成 = NEW=0 且 RETRY=0 (DONE+MISS+INVALID_ACCESSION = 921600)
未完成 = 仍在跑, 只做进度简报: 判定数/921600、RETRY 数、full_mapping.log 尾部 progress 行、服务 is-active。

## Step 1: EBI 补跑 (只补 status='MISS' 的 target; 断点续跑)
cd /public/home/sjl2/datasetdb/gene_seqs/full_gene
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy FTP_PROXY ftp_proxy ALL_PROXY all_proxy
nohup /usr/bin/python3 -u v4_runner.py fetch_ebi_coordinates.py \
  --mapping-db /public/home/sjl2/datasetdb/gene_seqs/full_gene/full_mapping/ipg_mapping.sqlite \
  --output /public/home/sjl2/datasetdb/gene_seqs/full_gene/full_mapping_ebi \
  --batch-size 50 --workers 4 --attempts 8 --rounds 5 >> full_mapping_ebi.log 2>&1 &
- 必须走 v4_runner.py (强制 IPv4) 且 unset 代理 (systemd/会话环境的代理会弄坏 TLS)。
- 幂等: 重跑自动续 (ebi_coordinates.sqlite 内 NEW/RETRY 断点)。
- 完成判定: full_mapping_ebi.log 出现 SUMMARY 行, 且 ebi_coordinates.sqlite 中 NEW+RETRY=0。

## Step 2: 导入坐标 (经 stage 库, 先备份)
cd /public/home/sjl2/datasetdb/gene_seqs/full_gene
cp /public/home/sjl2/datasetdb/dataset.db /public/home/sjl2/datasetdb/dataset_stage_gene.db
/usr/bin/python3 -u import_gene_coverage.py import \
  --db /public/home/sjl2/datasetdb/dataset_stage_gene.db \
  --ncbi-db /public/home/sjl2/datasetdb/gene_seqs/full_gene/full_mapping/ipg_mapping.sqlite \
  --ebi-db /public/home/sjl2/datasetdb/gene_seqs/full_gene/full_mapping_ebi/ebi_coordinates.sqlite \
  --summary /public/home/sjl2/datasetdb/gene_seqs/full_gene/gene_coverage_import.full.json
- 不传 --validation (CDS 未跑); 若报 cds_validation 表缺失, 生成仅表头的
  cds_validation.tsv (accession,fetch_status,validation_status,error) 再加 --validation 重跑。
- 校验: python3 -c "import sqlite3;db=sqlite3.connect('.../dataset_stage_gene.db');print(db.execute('PRAGMA integrity_check').fetchone()[0]);print(db.execute('SELECT COUNT(*) FROM gene_coordinates').fetchone()[0])"
  integrity 必须为 ok 且 gene_coordinates > 0。
- 上线: cp /public/home/sjl2/datasetdb/dataset.db /public/home/sjl2/datasetdb/dataset_backup_<日期>.db && mv dataset_stage_gene.db /public/home/sjl2/datasetdb/dataset.db

## Step 3: 重建站点
cd /public/home/sjl2/envtoldb_site && python3 generator/build_static_site_en.py
(读 dataset.db + config.json, 输出到 repo 根; 确认 index.html 的 release badge / DATA_AS_OF 更新)

## Step 4: 提交推送
cd /public/home/sjl2/envtoldb_site
git add -A && git commit -m "v3.6.0: full gene coordinates — 921,600 proteins mapped (NCBI IPG + EBI supplement)" && git push origin main
(工作区原有 311 个文件的未提交改进会一并提交; GitHub SSH 认证已验证可用)

## Step 5: 线上验证
curl -s https://jialiangsun873-pixel.github.io/EnvtolDB/index.html | grep -oE 'v3\.[0-9.]+'
(与 RELEASE 版本号一致即成功; GitHub Pages 可能有 1-2 分钟延迟)

## 防重复
若 git log -1 --format=%s 已含 "full gene coordinates" 或线上版本已是 v3.6.0 → 本轮只需汇报"已完成"。

## 已知雷区
- fetch 一律走 v4_runner.py (IPv6 到 NCBI/EBI 会坏 TLS) + unset 代理。
- 不要动运行中实例的 ipg_raw/*.tmp.* 文件。
- dataset.db 替换前必须先备份; emotion 站点/网关对该库以读为主, 换文件安全。
- 大批次 (GB 级) 响应是正常现象 (超普遍蛋白), 不要按"污染"重置; timeout 已提到 600s。
## 补充 (2026-11-25 上午实测)
- dataset.db 目前没有 gene_coordinates / protein_gene_coverage 表 — import 前先建 schema:
  /usr/bin/python3 -u import_gene_coverage.py schema --db <stage_db>
  然后再跑 import (import 命令若自带建表则跳过 schema 步骤)。
- EBI 补跑实测命中率远高于早期抽样: DONE:NO_COORDINATES 约 80:20 (早期 1:8 是按 accession 字母序的偏差)。
- 导入后校验建议: gene_coordinates 行数应接近 IPG DONE + EBI DONE 之和 (减去重复锚定)。
