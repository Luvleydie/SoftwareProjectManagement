from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("documento.pdf")
with open("salida.md", "w", encoding="utf-8") as f:
    f.write(result.text_content)