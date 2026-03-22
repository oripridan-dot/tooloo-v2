with open("engine/self_improvement.py", "r") as f:
    text = f.read()

parts = text.split("    def _implement_top_assessments(")
if len(parts) > 2:
    # there is a duplicate
    print("Fixing duplicate...")
    
    # Let's cleanly replace
    import re
    cleaned = re.sub(
        r"    def _implement_top_assessments\(.*?pass\n",
        "",
        text,
        count=1,
        flags=re.DOTALL
    )
    with open("engine/self_improvement.py", "w") as f:
        f.write(cleaned)
    print("Duplicate removed.")
