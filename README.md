
# Grocery Price Comparator (Bonpreu & DIA)

**Goal**  
Quickly find where a given grocery product is **cheapest**, both by unit price and by price-per-kg, comparing two Spanish supermarket chains.

---

## 🛠️ Workflow

### 1️⃣ Scraping
Use the provided Python scripts to collect product data.

**Bonpreu / Esclat**
```bash
python scraping_bonpreu2.py "CATEGORY_URL" --step 90 --max-loops 200 --passes 0
````

**DIA**

```bash
python scraping_dia.py "CATEGORY_URL"
```

> Replace `CATEGORY_URL` with the desired category page.
> Each run saves one CSV per category inside the `Data/` folder.

---

### 2️⃣ Merging & Cleaning

Merge all downloaded CSVs using the Jupyter notebooks:

* `merge_bonpreu.ipynb`
* `merge_dia.ipynb`

These notebooks create two clean, unified files:

```
bonpreu_merged_clean.csv
dia_merged_clean.csv
```

---

### 3️⃣ Price Comparison

Open `Notebook.ipynb` and run:

```python
best_for("gnocchi")
```

This returns a table showing:

* **Min / Max absolute price**
* **Min / Max price per kilogram**

for all matching products across both supermarkets.

---

## 📂 Folder Structure

```
Data/
├── Bonpreu/          # Raw CSVs scraped from Bonpreu
├── DIA/              # Raw CSVs scraped from DIA
└── merged_clean/     # Clean merged CSVs
scripts/
├── scraping_bonpreu2.py
└── scraping_dia.py
notebooks/
├── merge_bonpreu.ipynb
├── merge_dia.ipynb
└── Notebook.ipynb    # Price comparison & queries
```

---

## ⚠️ Notes

* **Educational purpose only.**
* Respect each supermarket’s terms of use and avoid excessive requests.
* Tested with Python 3.10+, `selenium`, `undetected-chromedriver`, and `pandas`.

---

## 📜 License

MIT License – see [LICENSE](LICENSE) for details.


