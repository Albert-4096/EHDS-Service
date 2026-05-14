from fhir.resources.encounter import Encounter
print(Encounter.model_fields['class_fhir'].annotation)
