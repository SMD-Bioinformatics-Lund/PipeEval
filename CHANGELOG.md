# 2.0.0

* Generalized run module to allow any pipeline
* Refactored eval module to reduce amount of code in main function
* Generalized eval module to allow configuration for different pipelines

# 1.4.0

* Add run types for oncov1, myeloid-const, modycf
* Rename run types to follow the profile names rather than dataset names
* --analysis and --assay flags for run mode to allow overriding the CSV fields
* Diffing QC files

# 1.3.1

* Put proper quoting on pipeline arguments in resume.sh

# 1.3.0

* Fix issue where ignored files were still listed as missing during evaluation
* Fix issue with automatic tagging where wrong version pattern was used
* --silent flag to only log warning or higher level logs
* Graceful exit if running with --baseline without configuring --baseline_repo
* Pytest check that Python version matches latest CHANGELOG version
* Add agents instructions to not change formatting of the code
* Add command --all_variants to output a score comparison including shared variants with the same score
* Refactor paths and configurations into two separate classes passed instead of individual parameters for high-level functions

# 1.2.2

* Add mypy CI
* Auto tag using changelog

# 1.2.1

* Add GitHub actions workflows
* Extended unit testing

# 1.2.0

* Reorganizing code with "commands" folder and "shared" for shared code
* Adding command "vcf" for direct comparison of VCF files
* Added first minimal regression test for main.py vcf subcommand (to be expanded on later)

# 1.1.2

* Include assay and diagnosis in config and generated CSV

# 1.1.1

* Optional line number in outputs by "-n" or "--show_line_numbers" flag

# 1.1.0

* Show total number of variants in scored comparisons
* Simplify README by removing help printout
* Pretty print variant presence/absence
* Update "tag" to "label" in run.log
* When running eval with verbose, show the real matching paths instead of with placeholder and show base dir if not matching
* Add header to annotation output and separate columns for pos and ref/alt
* If outpath is provided, write all variant presence entries to file

# 1.0.4

* Calculate length through END - pos + 1

# 1.0.3

* Skip confirmation skips the Git pull confirmation as well

# 1.0.2

* Info about no anntation keys found when present in one

# 1.0.1

* Fix missing .items

# 1.0.0

* First release. Both runner and eval seems to cover basic needs.
