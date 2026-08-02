# Best Gift Search（最佳礼物搜索）

Best Gift Search 是一个可运行、可解释、可评测的多 Agent 电商礼物导购项目。系统会理解收礼人、场景、兴趣、预算和配送国家，并行调用不同专长的 Agent，最后根据商品相关性、价格、运费、评分和多样性生成推荐。

## 在线体验

- [GitHub Pages 公开交互演示](https://irenezhangtt.github.io/BestGiftSearch-AI-Agent/)
- [GitHub 仓库](https://github.com/Irenezhangtt/BestGiftSearch-AI-Agent)

GitHub Pages 使用代表性数据，不需要后端或 API Key。完整功能需要在本地或服务器运行，其中包含 FastAPI、WebSocket 实时事件、SQLite 记忆、用户反馈、异步任务和质量评测。

## 最快启动方式

需要安装 Docker Desktop，并确保 `5173` 和 `8000` 端口可用。

```bash
git clone https://github.com/Irenezhangtt/BestGiftSearch-AI-Agent.git
cd BestGiftSearch-AI-Agent
cp .env.example .env
docker compose up --build
```

启动后打开：

- 前端：<http://localhost:5173>
- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>

默认是确定性演示模式，不需要任何付费服务或密钥。

## 不使用 Docker

需要 Python 3.12+、[uv](https://docs.astral.sh/uv/) 和 Node.js 22+。

后端终端：

```bash
cp .env.example .env
uv sync --extra dev
uv run uvicorn best_gift_search.app:app --reload --port 8000
```

前端终端：

```bash
cd web
npm install
npm run dev
```

## 如何使用

1. 输入收礼人、节日或场景、兴趣、预算，例如：`给喜欢咖啡和旅行的姐姐买生日礼物，预算 80 美元以内`。
2. 选择配送国家并开始搜索。
3. 查看 `think → act → observe → reflect` 实时 Agent 轨迹。
4. 对比商品总价、匹配原因、风险提示和自动质量评分。
5. 对结果提供 Yes/No 反馈；系统会把偏好写入 SQLite，供同一用户后续搜索使用。

## 系统结构

```text
React/Vite 前端 ── REST + WebSocket ── FastAPI
                                         │
                                    AgentLoop
                          ┌──────────────┼──────────────┐
                     Recipient       Catalog         Value
                       Agent          Agent           Agent
                          └──────────────┼──────────────┘
                                  排序与反思
                                         │
                              SQLite 记忆与事件记录
```

## 可选 OpenAI Provider

```bash
pip install '.[ai]'
export OPENAI_API_KEY='你的密钥'
export BEST_GIFT_MODEL_PROVIDER=openai
export BEST_GIFT_OPENAI_MODEL=gpt-5.6-luna
```

密钥只应保存在服务端，不要写进 Vite 变量或提交到 GitHub。模型调用失败或超时后，系统会自动降级到确定性总结。

## 测试和评测

```bash
uv run pytest
uv run python -m best_gift_search.eval_runner evaluations/gift_search.jsonl --minimum 55
cd web && npm run build
```

评测覆盖相关性、预算匹配、多样性和可解释性。GitHub Actions 会在推送和 Pull Request 时重复执行这些检查。

## 生产环境注意事项

- 设置 `BEST_GIFT_CORS` 为真实前端域名，多个域名使用逗号分隔。
- 可通过 `BEST_GIFT_API_KEY` 开启共享 API Key 保护；正式用户认证建议使用 OIDC 网关。
- `BEST_GIFT_CATALOG_URL` 必须是 HTTPS，返回内容需要符合 `Product` schema。
- 多进程部署应把进程内任务调度器替换成 Redis/Celery、Dramatiq 或托管队列。
- 保留价格更新时间、商家可靠性检查以及地区隐私与用户同意机制。

更多细节请阅读 [架构文档](docs/ARCHITECTURE.md)、[运维文档](docs/OPERATIONS.md) 和英文版 [README](README.md)。
