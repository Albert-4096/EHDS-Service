import fhir.resources.medicationstatement as ms
import inspect

print(f"Members of fhir.resources.medicationstatement:")
for name, obj in inspect.getmembers(ms):
    if inspect.isclass(obj):
        print(f"Class: {name}")

from fhir.resources.medicationstatement import MedicationStatement
print("\nMedicationStatement fields:")
print(MedicationStatement.model_fields.keys())
