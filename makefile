run:
	# build image if not already exists
	test $$(docker images -q pypelines) || make build
	# rebuild python packages to force fresh packages, then execute
	docker compose up --scale worker=10

build:
	docker build . -t pypelines

.PHONY: build
