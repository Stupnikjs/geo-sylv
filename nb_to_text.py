import json

with open("notebook.ipynb", "r", encoding="utf-8") as f:
    notebook = json.load(f)

code = []

for cell in notebook["cells"]:
    if cell["cell_type"] == "code":
        code.append("".join(cell["source"]))

with open("code.txt", "w", encoding="utf-8") as f:
    f.write("\n\n".join(code))