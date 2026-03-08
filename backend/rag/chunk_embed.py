import google.generativeai as genai
genai.configure(api_key="AIzaSyDozsOntE3QCTzDMLNbrnzccuCGuaTkoJs")
for m in genai.list_models():
    if "embed" in m.name:
        print(m.name, m.supported_generation_methods)