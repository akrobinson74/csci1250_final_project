# CSCI-1250 Final Project

## Setup

1. Install uv (MacOs):
   https://docs.astral.sh/uv/getting-started/installation/

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Checkout the project:

```
git clone https://github.com/akrobinson74/csci1250_final_project.git
# OR
git clone git@github.com:akrobinson74/csci1250_final_project.git
```

3. Install dependencies:

```
uv sync
```

4. Activate the virtual environment:

```bash
source ./venv/bin/activate
```

Powershell:

```powershell
.venv\Scripts\activate
```

5. Have fun with the game:

```
uv run main.py
```
