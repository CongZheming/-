# Coding Rules

## Project Principles

1. This project is a local research assistant, not a crawler.
2. Do not implement automated scraping, login bypass, anti-bot bypass, or platform restriction circumvention.
3. Keep all research materials in local SQLite and local export files.
4. Prefer stable rule-based logic for V1.0. Advanced models should be optional.
5. Keep Chinese online expressions, abbreviations, sarcasm, homophones, and emoji during cleaning.

## Code Style

1. Use clear function names and small modules.
2. Keep Streamlit UI simple and suitable for research demonstration.
3. Avoid over-cleaning text; raw material integrity matters for qualitative research.
4. Database writes should use parameterized SQL.
5. Export files should be written under `data/output/`.

## Research Workflow

1. Researcher manually collects screenshots or text.
2. System cleans and recommends labels.
3. Researcher reviews and confirms final labels.
4. Reviewed data can be exported for coding, statistics, clustering, or qualitative analysis.
