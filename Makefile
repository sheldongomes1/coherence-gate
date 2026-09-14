# Coherence Gate — one command per success criterion (GOAL.md).
# Requires: uv (https://docs.astral.sh/uv/) and a .env with both API keys.
UV      ?= uv
PY      := $(UV) run python
RUN_DIR ?= runs

.PHONY: help setup demo eval test lint trace models report clean site deploy-site golden parse ablation check eval-diff brief showcase eval-txt

help:
	@echo "make setup   - create venv + install deps (uv sync)"
	@echo "make test    - unit tests (deterministic core; no API calls)"
	@echo "make eval    - full pipeline over golden/ then score vs manifest -> eval_report.md"
	@echo "make demo    - the 5-minute walkthrough (G11 auto-clear, G10 absence, G09 trap, report, trace)"
	@echo "make trace   - pretty-print the latest run's trace.jsonl"
	@echo "make report  - re-render run_report.html for the latest run"
	@echo "make models  - list live model ids on both APIs (verify pins in config/models.yaml)"

setup:
	$(UV) sync --extra dev
	@test -f .env || (cp .env.example .env && echo ">> wrote .env — fill in GOOGLE_API_KEY and ANTHROPIC_API_KEY")

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check src tests

eval:            ## default source: parsed PDF (Mixedbread); parse artifacts cached in golden/parsed
	$(PY) -m coherence_gate.cli eval --golden golden --out $(RUN_DIR) --source pdf

eval-txt:        ## ablation baseline: canonical text, no parsing
	$(PY) -m coherence_gate.cli eval --golden golden --out $(RUN_DIR) --source txt

parse:           ## pre-parse every golden PDF (versioned artifacts in golden/parsed)
	$(PY) -m coherence_gate.cli parse --golden golden

ablation:        ## make ablation TXT=runs/<ts> PDF=runs/<ts>
	$(PY) -m coherence_gate.cli ablation --txt-run $(TXT) --pdf-run $(PDF)

demo:
	$(PY) -m coherence_gate.cli demo --golden golden --out $(RUN_DIR)

trace:
	$(PY) -m coherence_gate.cli trace --latest $(RUN_DIR)

report:
	$(PY) -m coherence_gate.cli report --latest $(RUN_DIR)

models:
	$(PY) scripts/list_models.py

clean:
	rm -rf $(RUN_DIR)/2* .pytest_cache .ruff_cache

showcase:
	@test -n "$(RUN)" || (echo "usage: make showcase RUN=runs/<ts>"; exit 1)
	rm -rf runs/showcase && cp -r $(RUN) runs/showcase && echo "frozen $(RUN) -> runs/showcase (eval run); runs/showcase-demo holds a frozen make demo run"

brief:
	@test -n "$(RUN)" || (echo "usage: make brief RUN=runs/<ts>"; exit 1)
	$(PY) scripts/fill_brief.py $(RUN)

golden:
	$(PY) scripts/gen_golden.py

check:           ## make check DOC=path/to/doc.pdf [TRADE=id]
	$(PY) -m coherence_gate.cli check $(DOC) $(if $(TRADE),--trade $(TRADE),) --out $(RUN_DIR)/check

eval-diff:       ## make eval-diff A=runs/<baseline> B=runs/<candidate>
	$(PY) scripts/eval_diff.py $(A)/summary.json $(B)/summary.json > eval_diff.md && echo wrote eval_diff.md

site:            ## assemble a self-contained static site (desk view = index.html) in site/
	$(PY) scripts/build_site.py

trace-export:    ## load a run's trace into BigQuery. make trace-export RUN=runs/showcase [DRY=1]
	$(PY) -m coherence_gate.cli trace-export --run $(RUN) $(if $(DRY),--dry-run,)

agent-engine:    ## preflight the Vertex AI Agent Engine deployment (creates nothing)
	$(PY) scripts/deploy_agent_engine.py

adk-check:       ## install google-adk (optional) and assert the ADK path gives an identical result
	uv pip install google-adk
	uv run pytest -q tests/test_adk_wrapper.py

deploy-service:  ## Cloud Run live service (FastAPI, Dockerfile at root). make deploy-service PROJECT=... REGION=us-central1
	gcloud run deploy coherence-gate-demo --source . --project $(PROJECT) --region $(REGION) --allow-unauthenticated --quiet \
	  --min-instances 1 --max-instances 1 --no-cpu-throttling --cpu-boost \
	  --set-secrets GOOGLE_API_KEY=cg-google-api-key:latest,ANTHROPIC_API_KEY=cg-anthropic-api-key:latest,MXBAI_API_KEY=cg-mxbai-api-key:latest

deploy-site:     ## Cloud Run static site (nginx). make deploy-site PROJECT=... REGION=us-central1
	@test -d site || $(MAKE) site
	gcloud run deploy coherence-gate-demo --source site --project $(PROJECT) --region $(REGION) --allow-unauthenticated --quiet
