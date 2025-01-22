# 1.2.0

* Reorganizing code with "commands" folder and "shared" for shared code
* Adding command "vcf" for direct comparison of VCF files

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