from dotenv import load_dotenv
import requests
import os

load_dotenv()  # Carrega variáveis do .env

class AIClient:
    from typing import Optional

    def __init__(self, api_url: str = "https://api.x.ai/v1/chat/completions", api_key: Optional[str] = None) -> None:
        self.api_url = api_url or os.environ.get("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
        self.api_key = api_key or os.environ.get("GROK_API_KEY")

    def classify_email(self, email_content: str) -> str:
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'text': email_content
        }
        response = requests.post(f'{self.api_url}/classify', headers=headers, json=data)
        response.raise_for_status()
        return response.json().get('category', 'Unknown')

    def generate_response(self, data: dict[str, object], input_data: dict[str, object], category: str, original_text: str) -> str:
        if not self.api_key:
            if category == "Produtivo":
                return "Obrigado pelo contato. Recebi sua mensagem e vou analisar/acionar o responsável. Retorno em breve com uma atualização."
            return "Agradeço a mensagem. Registro-a e, caso seja necessário, entrarei em contato. Desejo um ótimo dia."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = [
            {
                "role": "system",
                "content": "Você é um assistente profissional que responde emails de acordo com a categoria informada."
            },
            {
                "role": "user",
                "content": f"Categoria: {category}\nEmail: {original_text}\nGere uma resposta breve e adequada."
            }
        ]
        data = {
            "model": "grok-4-latest",
            "messages": messages,
            "stream": False,
            "temperature": 0.2,
            "max_tokens": 120
        }
        try:
            resp = requests.post(self.api_url, headers=headers, json=data, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Erro ao gerar via Grok: {e}"

# Função de módulo para integração com outros arquivos
def generate_response(category: str, original_text: str) -> str:
    ai = AIClient()
    return ai.generate_response({}, {}, category=category, original_text=original_text)

# Teste rápido
if __name__ == "__main__":
    resposta = generate_response("Produtivo", "Preciso de suporte urgente.")
    print(resposta)