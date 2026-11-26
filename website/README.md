# neuDB website

Static, dependency-free landing page and local database dashboard for neuDB. There is no build step, framework, analytics, remote font, or third-party JavaScript. Brand assets are local SVGs and raster derivatives.

## Run locally

From the repository root:

```bash
python3 -m http.server 8080 --directory website
```

Open <http://127.0.0.1:8080>. The dashboard is at <http://127.0.0.1:8080/dashboard.html>.

## Connect the local dashboard

Install the API extra from the source checkout and start exactly one API process:

```bash
python -m pip install -e ".[api]"
export NEUDB_API_KEY='replace-with-a-long-random-value'
NEUDB_API_DB=neudb_api_data \
NEUDB_CORS_ORIGINS=http://127.0.0.1:8080 \
uvicorn neudb.api:app --host 127.0.0.1 --port 8000
```

The dashboard accepts only HTTP localhost API URLs and keeps the entered key in the tab's session storage. It sends that key only to the selected local API. If you serve the site from another port, add that exact origin to `NEUDB_CORS_ORIGINS`.

**HTTPS-to-localhost warning:** an HTTPS page, including the deployed GitHub Pages site, may be blocked from fetching an HTTP localhost API by mixed-content or Private Network Access rules. The deployed landing page remains useful, but serve the dashboard locally over HTTP for a reliable connection. The API is not multi-tenant and must not be exposed as a shared or production service.

## Structure

```text
website/
├── index.html          # Landing page
├── dashboard.html      # Local-only API dashboard
├── README.md
├── assets/             # Brand SVGs, social card, and raster icons
├── css/
│   ├── style.css       # Landing page styles
│   └── dashboard.css   # Dashboard styles
└── js/
    ├── main.js         # Simulated demo, tabs, navigation
    ├── dashboard.js    # Local API client and pagination
    └── background.js   # Decorative hero canvas
```

The hero interaction is explicitly labeled as a simulated demo. It uses canned responses and never connects to a database or LLM.

## GitHub Pages deployment

Deployment is already defined in [`.github/workflows/pages.yml`](../.github/workflows/pages.yml). On pushes to `main` that change `website/**` or `docs/brand/**`, and on manual workflow dispatch, it:

1. checks out the repository;
2. copies canonical brand files from `docs/brand/` into `website/assets/`;
3. uploads `website/` as a Pages artifact;
4. deploys it with `actions/deploy-pages`.

The published site is <https://sajadxdp0.github.io/neudb/>. GitHub Pages must be enabled with GitHub Actions as the source. No branch-based `gh-pages` workflow is needed.

## Update brand assets

Canonical files live in [`docs/brand/`](../docs/brand/README.md). The workflow syncs them during deployment. After a local change:

```bash
cp docs/brand/* website/assets/
```

See the brand guide for SVG usage rules and raster regeneration commands.

## Privacy and network egress

- The static site loads no remote fonts, scripts, images, or analytics.
- Core neuDB storage and search are local.
- The first embedding use downloads `sentence-transformers/all-MiniLM-L6-v2` when the `agent` or `embeddings` extra is installed.
- Ollama is restricted to localhost by default. The OpenAI agent sends the system prompt, retrieved memory context, and current message to OpenAI.
- The dashboard sends the API key only to the validated localhost API URL entered by the user. It does not contact a hosted neuDB service.

Product documentation lives in [`docs/`](../docs/README.md); installation is source-first via the [README](../README.md#install-from-source).
