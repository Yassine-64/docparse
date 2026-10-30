.PHONY: install lint type test check run eval
install: ; uv sync --all-extras
lint:    ; uv run ruff check . && uv run ruff format --check .
fmt:     ; uv run ruff format . && uv run ruff check --fix .
type:    ; uv run mypy
test:    ; uv run pytest -q
check:   lint type test
run:     ; uv run docparse serve --reload
up:      ; docker compose -f docker/docker-compose.yml up --build
eval:    ; uv run python evals/run_eval.py evals/data
