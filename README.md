# Outline

* Requirements
* Outline of what it does
* Runner
* Evaluator
* Setting things up on the server (maybe for the wiki)

# Requirements

* Written to be compatible with version 3.6 (the version running on our cluster)

# Running the Runner

```{python}
python3 main.py run \
    --checkout jw_update_genmod \
    --baseout out/genmod \
    --config default.config \
    --run_type giab_single \
    --start_data bam \
    --repo /path/to/repo \
    --label run1
```

# Running the evaluator

```{python}
python3 main.py eval \
    --results1 /path/results1 \
    --results2 /path/results2 \
    --config runner/default.config \
    --outdir /path/eval_out \
    --comparisons default
```