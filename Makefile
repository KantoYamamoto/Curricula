.PHONY: test export check serve
export:
	swift run curricula export data/releases/pilot-0.1.0.json
	swift run curricula export-examples data/releases
	swift run curricula export-cross-subjects data/releases/cross-subject-0.1.0.json

test:
	swift test
	python3 -m unittest discover -s scripts -p 'test_*.py' -v
	python3 scripts/check_contract.py

check: test
	@tmp=$$(mktemp); swift run curricula export $$tmp && cmp $$tmp data/releases/pilot-0.1.0.json; status=$$?; rm -f $$tmp; exit $$status

	@tmp=$$(mktemp -d); swift run curricula export-examples $$tmp && cmp $$tmp/examples-0.1.0.json data/releases/examples-0.1.0.json && cmp $$tmp/examples-0.2.0.json data/releases/examples-0.2.0.json; status=$$?; rm -f $$tmp/examples-0.1.0.json $$tmp/examples-0.2.0.json; rmdir $$tmp; exit $$status

	@tmp=$$(mktemp); swift run curricula export-cross-subjects $$tmp && cmp $$tmp data/releases/cross-subject-0.1.0.json; status=$$?; rm -f $$tmp; exit $$status

serve:
	python3 scripts/serve.py
