from fhir.resources.medicationstatement import MedicationStatement
print(MedicationStatement.model_fields['dosage'].annotation)
