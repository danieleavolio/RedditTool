"""Dataset builder: a YAML recipe turns a collection into a clean, reproducible dataset.

Kept free of imports on purpose: ``recipe``, ``builder`` and ``export`` import each other's
helpers, and an eager package ``__init__`` would make that circular.
"""
