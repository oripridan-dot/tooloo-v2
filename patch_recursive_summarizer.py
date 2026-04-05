from pathlib import Path
content = Path('engine/recursive_summarizer.py').read_text()
# Add missing save_entries since save_entry exists
content = content.replace('self.buddy_store.save_entry(e)', 'self.buddy_store.save_entry(e)')
