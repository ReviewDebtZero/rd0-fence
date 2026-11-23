# `slugify` drops non-ASCII letters

`utils/text.py::slugify("Café au lait")` returns `"caf-au-lait"`. It should keep letters by transliterating them
(`"cafe-au-lait"`). Please add a test.
