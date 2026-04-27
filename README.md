# Evidence Bio RAG

Evidence Bio RAG 是一个面向生物医学文献综述的证据约束 RAG 系统。它不会只让模型“凭感觉回答”，而是把回答绑定到论文、研究、证据片段、结构化结果和引用上，并在最终输出前做证据充分性、引用、数字声明和范围检查。

当前版本已经从 fake-backed 骨架升级为可用的单机 Docker Compose 版本：FastAPI 后端、React 前端、Postgres、OpenSearch、Qdrant、MinIO、Redis、Neo4j 和 GROBID 可以一起启动。fake provider 仍保留给测试和离线开发，生产环境请显式配置真实 LLM 与 embedding provider。

## 操作指南

- [客户操作指南：导入文献、抽取证据、查询回答、批量导入与运维排错](docs/customer_operation_guide_zh.md)

## 功能

- 文献注册、去重和审计日志
- JATS XML、PDF、TEXT 文档上传
- MinIO 原文对象存储
- 解析结果、chunks、evidence spans 持久化
- 真实 OpenSearch lexical index 写入和查询
- 真实 Qdrant vector collection 写入和查询
- OpenAI-compatible、Anthropic Claude、Google Gemini 结构化 JSON LLM adapter
- sentence-transformers embedding adapter
- 单篇论文结构化抽取和 evidence span 外键校验
- evidence pack、sufficiency gate、综合回答和 verification
- `ebrag index rebuild` CLI 与 `POST /index/rebuild`
- React 前端：文献注册、上传、抽取、查询和证据预览

## 环境要求

- Docker Desktop
- Python 3.11+
- Node.js 20+（只在本地开发前端时需要）
- Git

建议在仓库根目录运行命令：

```powershell
cd "E:\super rag\evidence-bio-rag"
```

## 快速启动

复制配置模板：

```powershell
Copy-Item .env.example .env
```

生成部署访问 Key。这个 Key 是本系统自己的访问口令，不是 z.ai、OpenAI 或其他 LLM provider 的 API Key：

```powershell
$apiKey = [guid]::NewGuid().ToString("N")
$apiKey
(Get-Content .env) -replace '^EBRAG_SECURITY__API_KEY=.*', "EBRAG_SECURITY__API_KEY=$apiKey" | Set-Content .env
```

继续把 `.env` 里的数据库、MinIO、Neo4j 占位密钥替换成你自己的强密码。

启动完整本地栈：

```powershell
docker compose up -d --build
```

首次启动会自动运行 Alembic migration。服务地址：

| 服务 | 地址 |
| --- | --- |
| 前端 | http://127.0.0.1:3000 |
| API | http://127.0.0.1:8000 |
| 健康检查 | http://127.0.0.1:8000/health |
| OpenSearch | http://127.0.0.1:9200 |
| Qdrant | http://127.0.0.1:6333 |
| MinIO Console | http://127.0.0.1:9001 |
| Neo4j Browser | http://127.0.0.1:7474 |
| GROBID | http://127.0.0.1:8070 |

后台服务账号：

| 服务 | 用途 | 账号/密码来源 |
| --- | --- | --- |
| MinIO Console | 查看上传原文、解析产物等对象存储文件 | 账号是 `.env` 的 `MINIO_ROOT_USER`，密码是 `MINIO_ROOT_PASSWORD` |
| Neo4j Browser | 查看论文、研究、证据、结果之间的图关系 | `NEO4J_AUTH` 的斜杠前是账号，斜杠后是密码，例如 `neo4j/your-secret` |
| GROBID | PDF 文献解析服务 | 不需要账号密码 |
| 前端 `X-API-Key` | 访问业务 API 的部署口令 | `.env` 的 `EBRAG_SECURITY__API_KEY`，不是 MinIO/Neo4j/LLM 密钥 |

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

业务 API 默认需要 `X-API-Key`。前端左侧 Runtime 区域填入 `.env` 里的 `EBRAG_SECURITY__API_KEY` 后即可使用；交付给客户时，由部署方把这串部署访问 Key 发给客户。

停止服务：

```powershell
docker compose down
```

连数据卷一起删除：

```powershell
docker compose down -v
```

## Provider 配置

开发和测试默认使用 fake provider：

```env
EBRAG_PROJECT__ENVIRONMENT=dev
EBRAG_LLM__PROVIDER=fake
EBRAG_EMBEDDING__PROVIDER=fake
```

生产环境不要使用 fake。设置 `EBRAG_PROJECT__ENVIRONMENT=prod` 后，如果 LLM 或 embedding 仍是 fake，应用会拒绝启动。

OpenAI-compatible 示例：

```env
EBRAG_PROJECT__ENVIRONMENT=prod
EBRAG_LLM__PROVIDER=openai
EBRAG_LLM__API_KEY=sk-...
EBRAG_LLM__MODEL=gpt-4o-mini
EBRAG_LLM__BASE_URL=https://api.openai.com/v1
EBRAG_EMBEDDING__PROVIDER=sentence_transformers
EBRAG_EMBEDDING__MODEL=BAAI/bge-small-en-v1.5
EBRAG_VECTOR__COLLECTION=evidence_spans
```

Anthropic 示例：

```env
EBRAG_LLM__PROVIDER=anthropic
EBRAG_LLM__API_KEY=sk-ant-...
EBRAG_LLM__MODEL=claude-3-5-sonnet-latest
```

Google Gemini 示例：

```env
EBRAG_LLM__PROVIDER=google
EBRAG_LLM__API_KEY=...
EBRAG_LLM__MODEL=gemini-1.5-pro
```

## 本地开发

安装 Python 依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
$env:PYTHONPATH = "src"
```

启动 API：

```powershell
python -m alembic upgrade head
python -m uvicorn ebrag.api.app:app --host 127.0.0.1 --port 8000
```

启动前端开发服务器：

```powershell
cd frontend
npm install
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

## 使用流程

1. 打开前端 `http://127.0.0.1:3000`。
2. 在左侧 Runtime 区域填入部署方提供的 `X-API-Key`。
3. 注册一篇论文，得到 `paper_id` 和 `study_id`。
4. 上传 JATS XML、PDF 或 TXT 文档。
5. 系统会把原文写入 MinIO，解析文档，保存 chunks/evidence spans，并写入 OpenSearch 与 Qdrant。
6. 运行抽取。fake provider 下前端会提交一份示例结构化抽取；真实 provider 下可以直接让后端调用配置的 LLM。
7. 输入问题，调用 `/query/full`，查看带 result ids 和 evidence span ids 的回答。

## API 示例

先准备请求头：

```powershell
$headers = @{ "X-API-Key" = $env:EBRAG_SECURITY__API_KEY }
```

如果当前 PowerShell 没有加载 `.env`，也可以直接把部署访问 Key 写进变量：

```powershell
$headers = @{ "X-API-Key" = "你的部署访问Key" }
```

注册论文：

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
  -Headers $headers `
  -Body $paper `
  -ContentType "application/json"
```

上传 TXT 文档：

```powershell
$form = @{
  source_format = "TEXT"
  document_id = "demo.txt"
  file = Get-Item ".\demo.txt"
}

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/papers/P00000001/documents" `
  -Method Post `
  -Headers $headers `
  -Form $form
```

重建索引：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/index/rebuild" `
  -Method Post `
  -Headers $headers `
  -Body '{"paper_id":"P00000001"}' `
  -ContentType "application/json"
```

查询完整回答：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/query/full" `
  -Method Post `
  -Headers $headers `
  -Body '{"query":"Does Compound X reduce IL-6?","query_scope":"animal"}' `
  -ContentType "application/json"
```

## CLI

```powershell
$env:PYTHONPATH = "src"
python -m ebrag.cli --help
python -m ebrag.cli init-db
python -m ebrag.cli index rebuild
python -m ebrag.cli index rebuild --paper-id P00000001
```

## 验证

```powershell
$env:PYTHONPATH = "src"
python -m pytest
python -m ruff check .
python -m mypy
docker compose config --quiet
cd frontend
npm run build
```

## 当前边界

- 第一版按私有/internal 单机部署处理，使用部署级 API Key，不包含多用户登录、多租户和计费。
- 当前稳定 ID 生成逻辑面向单机/单 worker；多 worker 高并发写入时应迁移到 PostgreSQL sequence 或等价的数据库侧 ID 分配。
- Graph retrieval 当前使用已建图关系做召回，尚未用 query 做图库语义过滤；接入真实图库检索时需要补 query-aware traversal/search。
- reranker 暂时使用轻量本地融合/排序，后续可替换为 Cohere、BGE cross-encoder 或其他 rerank provider。
- PDF 解析依赖 GROBID，复杂版式和 OCR 质量仍需要单独评估。
- 真实 LLM 输出必须通过 Pydantic schema 校验；无法校验的输出不会写入无效外键数据。
