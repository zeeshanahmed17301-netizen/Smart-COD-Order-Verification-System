# Courier Location Scraper

This small scraper pulls branch locations from branches.pk for:

- leapard / Leopard Courier Service
- TCS
- postex

## Run

```powershell
python scrape_branches.py --output results.json
```

The script scans the site’s company index, follows the canonical company branch page when it exists, and exports structured branch rows with the branch name, address, phone number, and branch URL.

If a brand is not indexed on branches.pk, the output marks it as `not_indexed` instead of guessing.