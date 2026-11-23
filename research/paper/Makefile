# make -C research/paper  -> regenerates numbers, tables and figures from the benchmark results and builds both PDFs
PY ?= python3
all: numbers empirical tooldemo
numbers:
	$(PY) scripts/make_paper_numbers.py
empirical tooldemo:
	cd $@ && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
clean:
	cd empirical && latexmk -C; cd tooldemo && latexmk -C
.PHONY: all numbers empirical tooldemo clean
