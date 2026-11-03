import os
from google import genai

client = genai.Client()

def get_violões():
    import csv
    viol = []
    with open('Data/desafio_tecnico_ai_eng - products.csv') as f:
        for r in csv.DictReader(f):
            if r.get('category_id') == '5':
                p = float(r.get('price_brl') or 0)
                if p <= 1000 and r.get('stock_quantity') and int(r['stock_quantity']) > 0:
                    viol.append(f"• {r['name']} — R$ {r['price_brl']} (estoque: {r['stock_quantity']})")
    return "\n".join(viol)

def main():
    print("Bem-vindo ao Empório! Pergunte qualquer coisa.")
    while True:
        msg = input("\nVocê: ")
        if msg.lower() in ['sair', 'exit', 'q']:
            break
        dados = get_violões()
        resp = client.interactions.create(
            model="gemini-3.8-flash",
            input=f"Pergunta do cliente: {msg}\n\nDados da loja:\n{dados}\n\nResponda de forma humanizada, como atendente do Empório da Música."
        )
        print(f"\nEmpório: {resp.output_text}")

if __name__ == "__main__":
    main()
