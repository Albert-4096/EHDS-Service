import fhir.resources.device as device
import inspect

print(f"Members of fhir.resources.device:")
for name, obj in inspect.getmembers(device):
    if inspect.isclass(obj):
        print(f"Class: {name}")
