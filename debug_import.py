import sys
import trace

def trace_calls(frame, event, arg):
    if event == "call":
        func_name = frame.f_code.co_name
        file_name = frame.f_code.co_filename
        if "engine" in file_name or "studio" in file_name:
            print(f"CALL {file_name}:{frame.f_lineno} -> {func_name}")
    return trace_calls

sys.settrace(trace_calls)

print("Starting import...")
try:
    import studio.api
except Exception as e:
    print(f"Failed: {e}")
print("Import done!")
