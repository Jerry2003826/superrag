# Evidence Bio RAG

Evidence Bio RAG 是一个面向生物医学系统综述的证据约束 RAG 后端。

它的目标不是直接“凭模型回答”，而是把每个结论绑定到可追溯的证据对象：论文、研究、证据片段、结构化结果和引用。最终回答会经过证据充分性、引用、数字声明和范围检查，尽量避免 unsupported claim、uncited numeric claim 和 wrong-scope claim。

## 当前状态

当前仓库已经具备一个可本地运行的后端闭环骨架：

- FastAPI API 服务
- Postgres 数据库和 Alembic 迁移
- Docker Compose 本地基础设施
- 文献注册、去重、审计日志
- JATS/GROBID 解析基础路径
- 单篇论文结构化抽取流程
- 数字一致性检查和外键引用校验
- 结构化检索、证据包、sufficiency gate
- fake-backed lexical/vector/rerank/synthesis/verifier 流程
- 人审队列、评测入口和 GitHub Actions CI

还没有接入生产级真实 LLM、真实 embedding 模型、真实 reranker 和完整前端，所以它现在更适合做本地开发、流程验证和后续功能扩展。

## 环境要求

- Windows + PowerShell
- Docker Desktop
- Python 3.11+
- Git

建议所有命令都在仓库根目录运行：

```powershell
cd "E:\super rag\evidence-bio-rag"
```

## 首次安装

创建并安装 Python 环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

本地直接运行时建议显式设置 `PYTHONPATH`，避免 import 到旧的 editable install：

```powershell
$env:PYTHONPATH = "src"
```

## 启动本地服务

先启动 Docker Desktop，然后启动基础设施：

```powershell
docker compose up -d
```

查看容器状态：

```powershell
docker compose ps
```

本地服务地址：

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| API | http://127.0.0.1:8000 | FastAPI 后端 |
| API docs | http://127.0.0.1:8000/docs | 交互式接口文档 |
| Postgres | localhost:5432 | `ebrag / ebrag` |
| OpenSearch | http://localhost:9200 | 本地无鉴权单节点 |
| Qdrant | http://localhost:6333 | 向量库 |
| Neo4j | http://localhost:7474 | `neo4j / password` |
| MinIO | http://localhost:9001 | `minio / minio123` |
| Redis | localhost:6379 | 队列/缓存 |
| GROBID | http://localhost:8070 | PDF/文献解析服务 |

## 初始化数据库

使用 Alembic 跑迁移：

```powershell
$env:PYTHONPATH = "src"
python -m alembic upgrade head
```

如需回滚本地库：

```powershell
$env:PYTHONPATH = "src"
python -m alembic downgrade base
```

## 启动 API

```powershell
$env:PYTHONPATH = "src"
python -m uvicorn ebrag.api.app:app --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

预期返回：

```json
{
  "status": "ok"
}
```

然后打开：

```text
http://127.0.0.1:8000/docs
```

## 最小使用流程

### 1. 注册论文

接口：

```text
POST /papers/register
```

PowerShell 示例：

```powershell
$paper = @{
  title = "Compound X reduces IL-6 in APP/PS1 mice"
  doi = "10.0000/example-001"
  authors = @("Li", "Wang")
  year = 2026
  journal = "Local Test"
  abstract = "Compound X reduced IL-6 in a mouse model."
  source_database = "local"
  source_url = "http://localhost/example"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/papers/register" `
  -Method Post `
  -Body $paper `
  -ContentType "application/json"
```

返回示例：

```json
{
  "paper_id": "P00000001",
  "study_id": "S00000001",
  "report_id": "REP00000001",
  "duplicate_kind": null
}
```

### 2. 解析论文

接口：

```text
POST /papers/{paper_id}/parse
```

当前解析路由支持 JATS XML 优先，失败时走 GROBID fallback。最方便的方式是在 `http://127.0.0.1:8000/docs` 里直接填入请求体测试。

### 3. 跑结构化抽取

接口：

```text
POST /extraction/{paper_id}/run
```

当前抽取器使用 `FakeLLMClient`，所以请求里需要传入模拟的 LLM 输出：

```json
{
  "llm_output": {
    "paper_id": "P00000001",
    "extraction_status": "unverified",
    "results": [
      {
        "result_id": "R00000001",
        "study_id": "S00000001",
        "paper_id": "P00000001",
        "study_type": "animal",
        "population_or_model": "APP/PS1 mouse model",
        "species": "mouse",
        "cell_line": null,
        "intervention": "Compound X",
        "comparator": "vehicle",
        "outcome": "IL-6",
        "assay": "ELISA",
        "direction": "decreased",
        "effect_size": "32%",
        "p_value": "p=0.01",
        "confidence_interval": null,
        "sample_size": "n=12",
        "dose": "10 mg/kg",
        "duration": "8 weeks",
        "unit": "pg/mL",
        "scope": "animal",
        "evidence_span_id": "E00000001",
        "extraction_status": "unverified"
      }
    ]
  }
}
```

注意：`paper_id`、`study_id` 和 `evidence_span_id` 必须已经存在并且互相匹配。未知证据片段会被拒绝，不会写入无效外键。

### 4. 查询证据包

接口：

```text
POST /query/evidence-pack
```

请求示例：

```json
{
  "query": "Does Compound X reduce IL-6?",
  "query_scope": "animal"
}
```

它会返回一个 evidence pack，包括结构化结果、证据片段、检索分数和 sufficiency 状态。

### 5. 跑完整问答闭环

接口：

```text
POST /query/full
```

请求示例：

```json
{
  "query": "Does Compound X reduce IL-6?",
  "query_scope": "animal"
}
```

返回内容包含：

- `abstained`
- `block_reasons`
- `sufficiency`
- `answer`
- `claims`
- `verification`

如果证据不足或验证失败，最终 gate 会阻止不可靠回答。

### 6. 查看人审队列

接口：

```text
GET /review/queue
```

用于查看需要人工复核的 study report。

### 7. 跑评测

接口：

```text
POST /eval/run-gold
```

用于传入 gold cases 和 predictions，跑本地 regression/evaluation gate。

## 常用开发命令

运行测试：

```powershell
$env:PYTHONPATH = "src"
python -m pytest
```

运行 lint：

```powershell
$env:PYTHONPATH = "src"
python -m ruff check .
```

运行类型检查：

```powershell
$env:PYTHONPATH = "src"
python -m mypy
```

检查 Docker Compose 配置：

```powershell
docker compose config --quiet
```

停止容器：

```powershell
docker compose down
```

连数据卷一起删除：

```powershell
docker compose down -v
```

## CLI

当前 CLI 入口较少，主要用于初始化数据库元数据：

```powershell
$env:PYTHONPATH = "src"
python -m ebrag.cli --help
python -m ebrag.cli init-db
```

日常试用建议优先使用 FastAPI docs：

```text
http://127.0.0.1:8000/docs
```

## 当前限制

- API 查询链路里的 OpenSearch、vector、embedding、reranker、synthesis 和 LLM verifier 仍是 fake/mock 实现。
- MinIO 存储接口还只是基础占位，没有完整对象存储工作流。
- 真实 biomedical corpus ingestion、真实 PDF 批处理和大规模评测还没完成。
- 还没有前端页面；当前主要通过 FastAPI docs 或 HTTP 调用使用。

## 推荐下一步

1. 接入真实 LLM provider。
2. 接入真实 embedding 模型和 Qdrant collection。
3. 把 OpenSearch fake client 换成真实索引写入/查询。
4. 完成 MinIO 原文/解析产物存储。
5. 加一个简单前端或 notebook demo，让文献导入、抽取、查询更直观。
