.PHONY: install test info benchmark all figures clean

install:
	pip install .

test:
	pytest

info:
	zonemind info

benchmark:
	zonemind benchmark

all:
	zonemind all

figures:
	zonemind figures

clean:
	rm -rf results/*.json results/*.npz results/memory results/run.log
