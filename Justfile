set dotenv-load

lint:
  hatch fmt --linter --check

type:
  hatch env run -e type "pyright ."

format:
  hatch fmt --formatter

[confirm]
fix:
  hatch fmt --linter

test:
	hatch run test:cover

report: test
	hatch run +py=3.9 test:report

docs:
	hatch run docs:serve	

pages:
	hatch run docs:publish