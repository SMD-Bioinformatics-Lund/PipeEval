### Outline

The intent with PipeEval is to make more in-depths evaluation of results between pipeline changes easier and faster to carry out.

![overview](doc/pipeeval_overview.png)

### Requirements

Written to be compatible with version 3.6 (the version running on our cluster).

Only standard libs are currently used.

### Running the Runner

```{python}
python3 main.py run \
    --checkout jw_update_genmod \
    --base out/genmod \
    --run_profile giab_single \
    --start_data bam \
    --repo /path/to/repo \
    --label run1
```

Get more options by running:

```
python3 main.py run --help
```

### Running the evaluator

```{python}
python3 main.py eval \
    --results1 /path/results1 \
    --results2 /path/results2 \
    --outdir /path/eval_out \
    --comparisons default
```

```
python3 main.py eval --help
```

### Compare VCFs directly

```{python}
python3 main.py vcf \
    -1 /path/first.vcf.gz \
    -2 /path/second.vcf.gz
```

### Notes for developers

PipeEval is built to run in an environment where a legacy version (3.6) of Python still is used.
The most vivid consequence of this is that type hints aren't yet a built-in part of the language and must be imported. I.e. `list[str]` will crash, but `List[str]` (with `List` imported from `typing` library works).

Some expectations on the code:

* Formatted with `black` (run `black .` in the base dir - basic code formatting)
* Checked with `flake8` (run `flake8 .` in the base dir - code checks, such as missing variables etc)
* Formatted with `isort` (run `isort` in the base dir - organize the imports neatly)
* Type checked and passing `mypy` checks (run `mypy` in the base dir)
* When relevant, unit tested and passing unit tests (run `pytest .` in the base dir). Unit tests are not yet thoroughly implemented. If in doubt, you are probably fine skipping adding.

Some other style pointers:

* Use classes rather than nested dicts for complex data structures.
* Docstrings are not yet needed for functions. Might change in the future.
* Use clear variable names.
