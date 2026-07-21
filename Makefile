.PHONY: demo demo-dev demo-web-install demo-web-build demo-test

demo-web-install:
	npm --prefix apps/web ci

demo-web-build: demo-web-install
	npm --prefix apps/web run build

demo: demo-web-build
	PYTHONPATH=src:. python scripts/run_demo.py

demo-dev: demo-web-install
	PYTHONPATH=src:. python scripts/run_demo.py --dev

demo-test:
	PYTHONPATH=src pytest -q tests/runtime tests/demo_e2e tests/test_schemas.py tests/test_formatting_training.py
	npm --prefix apps/web test -- --run
