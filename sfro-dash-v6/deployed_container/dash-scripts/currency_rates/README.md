# Exchange Rates Monitor (`currency_rates`)

This directory contains the automated currency compiler script for the SFRO Dashboard V5. It queries the free, open-access Frankfurter API (referencing European Central Bank data) to retrieve the latest rates and historical 6-month high/low thresholds for any supported base and target currency pair.

---

## Directory Structure
*   `fetch_rates.py` - Core Python script that executes the API fetches, computes historical min/max values, and outputs the final JSON files.
*   `README.md` - This operations and maintenance guide.

---

## 1. Operations Guide (`fetch_rates.py`)

The script generates card configurations targeting the two text fallback cards on the dashboard.

### Command Line Arguments
| Argument | Default | Description |
| :--- | :--- | :--- |
| `-o`, `--out-dir` | `v5-test/data` | Output directory where the JSON files are stored |
| `--base` | `GBP` | The source base currency (e.g. `GBP`, `USD`, `EUR`) |
| `--left` | `ZAR` | The target currency for the left card (`fra400cap.json`) |
| `--right` | `USD` | The target currency for the right card (`q75cap.json`) |
| `--title-left` | `None` | Custom card header title for the left card (defaults to `"{base} to {left}"`) |
| `--title-right` | `None` | Custom card header title for the right card (defaults to `"{base} to {right}"`) |

### Command Examples

1.  **Standard defaults (GBP to ZAR and USD)**:
    ```bash
    python3 currency_rates/fetch_rates.py -o v5-test/data
    ```

2.  **Repurpose for USD base (USD to EUR and JPY)**:
    ```bash
    python3 currency_rates/fetch_rates.py -o v5-test/data --base USD --left EUR --right JPY
    ```

3.  **Repurpose with custom titles**:
    ```bash
    python3 currency_rates/fetch_rates.py -o v5-test/data --base GBP --left ZAR --right USD --title-left "Pound to Rand" --title-right "Pound to Dollar"
    ```

---

## 2. Dynamic Content Toggling (Scope vs Currency)

Because the dashboard frontend acts as a "dumb" client and dynamically renders card content based on whatever payload resides inside `fra400cap.json` and `q75cap.json`, you can **swap between scope forecast logs and exchange rates on the fly** simply by calling the respective compiler:

*   **To display Scope Forecasts**: Run the scope log compiler:
    ```bash
    python3 scope_forecast/fetch_captures.py -o v5-test/data
    ```
*   **To display Exchange Rates**: Run the currency compiler:
    ```bash
    python3 currency_rates/fetch_rates.py -o v5-test/data
    ```

---

## 3. JSON Outputs

The script writes two JSON files: `fra400cap.json` (left card) and `q75cap.json` (right card), adhering to the standard `"type": "text"` schema:

```json
{
  "title": "GBP to ZAR",
  "subtitle": "As of 2026-07-10",
  "type": "text",
  "data": {
    "text": "<div style='font-size: 2.6rem; font-weight: bold; margin-bottom: 0.6rem;'>21.91 ZAR</div><div style='font-size: 1.2rem; color: var(--muted); line-height: 1.3;'><div style='margin-bottom: 0.3rem;'>6M High: 22.87 ZAR</div><div>6M Low: 21.45 ZAR</div></div>"
  }
}
```

---

## 4. Production Scheduling

To schedule exchange rates to compile automatically (e.g., once every 4 hours), add the following to your system `cron` file:

```cron
0 */4 * * * cd /path/to/project && python3 currency_rates/fetch_rates.py -o sfro-dash-v5/data > /dev/null 2>&1
```
