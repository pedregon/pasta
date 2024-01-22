lint:
  hatch env run -e lint "ruff check ."

type:
  hatch env run -e type "pyright ."

format:
  hatch env run -e lint "ruff format ."

fix:
  hatch env run -e lint "ruff check --fix ."
