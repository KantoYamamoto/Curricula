.PHONY: test export check serve
export:
	swift run curricula export data/releases/pilot-0.1.0.json

test:
	swift test
	python3 -m unittest discover -s scripts -p 'test_*.py' -v
	python3 scripts/check_contract.py

check: test
	@tmp=$$(mktemp); swift run curricula export $$tmp && cmp $$tmp data/releases/pilot-0.1.0.json; status=$$?; rm -f $$tmp; exit $$status

serve:
	python3 scripts/serve.py
