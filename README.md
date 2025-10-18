# AI Batch Translate

A script to batch-translate JSON files using a local AI API.

---

## Prepare Data
- Use the queries in `queries/eBusiness-export.sql` to create the export JSON files with all texts.
- Then place the JSON files into the `data/todo/` directory.

## Setup

1.  **Create & Activate Virtual Environment**
    ```shell
    # Create the environment
    python -m venv venv

    # Activate it
    # Windows
    .\venv\Scripts\activate
    # macOS / Linux
    source venv/bin/activate
    ```

2.  **Install Dependencies**
    ```shell
    pip install -r requirements.txt
    ```

3.  **Configure Environment**
    ```shell
    # Copy the example file (use 'copy' on Windows)
    cp .env.example .env
    ```
    Now, **edit the `.env` file** to set your `AI_API_URL` and `AI_MODEL_NAME`.

---

## Running

1.  **Place** your JSON files into the `data/todo/` directory.

2.  **Execute** the script:
    ```shell
    python run_translator.py
    ```

3.  **Find** completed files in the `data/done/` directory. Check `processing.log` for details.