# Double JSON Converter

This script cleans up JSON files by converting double-encoded JSON arrays within values into native arrays.

**Example:**
```json
[
  {
    "products": "[{\"id\":1,\"name\":\"Product A\"},{\"id\":2,\"name\":\"Product B\"}]",
    "categories": "[{\"id\":10,\"name\":\"Category X\"},{\"id\":20,\"name\":\"Category Y\"}]"
  }
]
```

## Usage

The script is run from the command line and expects the path to the source file as an argument.

```shell
node clean-json.js <path/to/your/file.json>
```

The cleaned file is saved in a `dist` subfolder at the source file's location.

### Example

**Input Path:** `data/products.json`

**Command:**
```shell
node clean-json.js data/products.json
```

**Output Path:** `data/dist/products.json`