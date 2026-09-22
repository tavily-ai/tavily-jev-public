# Signal Desk: Tavily + jev

Build a local competitor-monitoring app with [Tavily](https://www.tavily.com/) and [jev](https://typesafe.ai/). Tavily finds recent news, product updates, and pricing information. jev evaluates each source against your company context and returns **Alert**, **Watch**, or **Ignore**.

This tutorial walks you through running the app, connecting your API keys, and creating your first briefing.

## How it works

1. Describe your company, the topics you care about, and up to five competitors.
2. Tavily searches for recent coverage and current product or pricing pages.
3. jev receives your company context and each retrieved source, then answers one Choice question: “How important is this source for this company?”
4. The app displays the returned decision, confidence, and probabilities alongside the original source passage and link.

The app uses a React frontend and a FastAPI backend. Classifications come directly from jev; the app does not override them or substitute sample results when a provider fails.

## 1. Install and start

You will need:

- Git and a Bash shell, such as macOS Terminal, Linux, or WSL.
- Node.js 20.19+ and npm.
- Python 3.10+, or [uv](https://docs.astral.sh/uv/) to create a Python 3.12 environment automatically.
- A [Tavily API key](https://app.tavily.com/) and a [jev API key](https://console.typesafe.ai/).

```bash
git clone https://github.com/tavily-ai/tavily-jev-public.git
cd tavily-jev-public
./setup.sh
./Start.command
```

Setup installs the locked Python dependencies and builds the frontend. Open **http://127.0.0.1:8765** and keep the terminal running. Press **Ctrl+C** to stop the server. On macOS, you can also double-click `Start.command` after setup.

## 2. Connect your API keys

Click **Connect API keys**, enter both keys, and save. Keys entered in the app stay in the local server process until it restarts. They are not saved in browser storage. A scan validates the keys by making real requests to both providers.

To keep your keys between restarts, create a local configuration file:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
TAVILY_API_KEY=your-tavily-key
TYPESAFE_API_KEY=your-jev-key
JEV_MODEL=jev-latest
```

jev uses the TypeSafe API, so its key is configured as `TYPESAFE_API_KEY`. Restart the server after changing `.env`. The file is excluded from Git; keep real keys out of commits and shared files.

## 3. Create your first briefing

1. Open **Edit context**. Start with the fictional company **Forma**, or describe your own company and customers.
2. Explain what matters to you, such as AI features, per-seat pricing, or integrations.
3. List up to five competitors, separated by commas. Website hints are optional.
4. Save, choose a search window, and click **Run daily scan**.
5. Filter the feed by **Alert**, **Watch**, or **Ignore**. Open any result to inspect the source passage, original link, and jev decision.

Both API keys are required. Each scan makes live provider requests and uses your account quotas. If a source cannot be evaluated, it remains visibly unclassified.

## Understand the results

- The selected day, week, or month window applies to the news search. Product and pricing pages provide current context; they do not establish that a price changed recently.
- The app evaluates up to 18 sources per scan. Tavily search responses are cached in memory for ten minutes.
- Scans run when you click the button. There is no background scheduler or notification delivery.
- Company settings are saved in `data/company.json`, which is excluded from Git. The feed clears on page reload.
- Competitor search queries go to Tavily. Your company context and retrieved source passages go to jev for evaluation.
- Model confidence is not proof that a source is correct. Follow the source link before acting on a result.

The provided launcher binds to `127.0.0.1` for local use. The app has no user accounts or rate limiting; add those controls before exposing a hosted instance to other users.

## Development

After setup, run the backend tests from the repository root:

```bash
.venv/bin/python -m pytest -q
```

To develop the frontend, keep the backend running and open a second terminal:

```bash
cd frontend
npm run dev
```

The Vite server proxies `/api` to the backend on port 8765. To rebuild the frontend served by the backend:

```bash
cd frontend
npm run build
```

The provider tests use mocks and do not consume API credits. To verify your own provider access, connect your keys and run a scan in the app.

## Learn more

- [Tavily website](https://www.tavily.com/) and [Search API reference](https://docs.tavily.com/documentation/api-reference/endpoint/search)
- [jev website](https://typesafe.ai/) and [API reference](https://docs.typesafe.ai/api)
- [jev Choice primitive](https://docs.typesafe.ai/primitives/choice)

## License

The source code is available under the [MIT License](LICENSE). Tavily logos and artwork are excluded from the code license; see [brand asset notes](frontend/public/brand/SOURCES.md).
