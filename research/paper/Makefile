# make -C research/paper  -> regenerates numbers, tables and figures from the benchmark results and builds the paper.
# tooldemo/ is a deferred draft (no committed PDF); build it with `make tooldemo` once gold-sheet labels exist.
PY ?= python3
all: numbers short
numbers:
	$(PY) scripts/make_paper_numbers.py
short tooldemo:
	cd $@ && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
clean:
	cd short && latexmk -c
	cd tooldemo && latexmk -c
.PHONY: all numbers short tooldemo clean
