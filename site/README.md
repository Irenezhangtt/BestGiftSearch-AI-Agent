# Best Gift Search showcase

This is the deployable, example-data showcase for Best Gift Search. It explains
the agent workflow and renders a representative recommendation result without
requiring a backend or secrets. The live React client is in `../web`; the
FastAPI agent service is in `../src/best_gift_search`.

```bash
npm ci
npm run dev
npm test
```

Requires Node.js 22.13 or newer. Hosting identity is persisted in
`.openai/hosting.json`; do not remove or replace its `project_id`.
