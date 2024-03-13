install-deps:
	pip3 install -r requirements.txt

build-scripts:
	go mod tidy && CGO_ENABLED=0 go build -o static_sync ./scripts/static/main.go

run: install-deps build-scripts
	python3 main.py
