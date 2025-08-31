from app import app
print('ENABLE_LLM =', app.config.get('ENABLE_LLM'))
print('ALLOW_UI_LLM_TOGGLE =', app.config.get('ALLOW_UI_LLM_TOGGLE'))
print('LLM_PROMPT_CONF_THRESHOLD =', app.config.get('LLM_PROMPT_CONF_THRESHOLD'))
