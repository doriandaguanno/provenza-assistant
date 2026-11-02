import json
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI

# ⚠️ REMETTEZ VOTRE CLÉ API ICI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
app = Flask(__name__)
CORS(app) # Autorise le site à communiquer avec ce serveur

DOSSIER_ACTUEL = os.path.dirname(os.path.abspath(__file__))

# --- OUTILS ---
def lire_tarifs():
    try:
        with open(os.path.join(DOSSIER_ACTUEL, "tarifs.txt"), "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Erreur : {e}"

def consulter_stock():
    try:
        with open(os.path.join(DOSSIER_ACTUEL, "stock.json"), "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Erreur : {e}"

def prendre_rendez_vous(nom_client, date_heure, objet):
    print(f"\n[Système] 📅 RENDEZ-VOUS PRIS : {nom_client} le {date_heure} pour : {objet}")
    return f"Le rendez-vous pour {nom_client} le {date_heure} concernant '{objet}' a bien été enregistré."

tools = [
    {
        "type": "function",
        "function": {
            "name": "lire_tarifs",
            "description": "OBLIGATOIRE. Appelle cette fonction pour TOUTE question sur les prix.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consulter_stock",
            "description": "OBLIGATOIRE. Appelle cette fonction pour les voitures en vente.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prendre_rendez_vous",
            "description": "Planifier un rendez-vous client.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nom_client": {"type": "string"},
                    "date_heure": {"type": "string"},
                    "objet": {"type": "string"}
                },
                "required": ["nom_client", "date_heure", "objet"],
            },
        },
    }
]

# --- ROUTE POUR LE SITE WEB ---
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    
    # On ajoute le prompt système au début
    messages.insert(0, {
        "role": "system", 
        "content": "Tu es l'assistant virtuel de Provenza Motors. RÈGLE ABSOLUE : Pour toute question sur les prix, tu DOIS IMPÉRATIVEMENT appeler l'outil 'lire_tarifs'. N'invente pas de réponse. Sois concis et professionnel."
    })

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Modèle ultra rapide et pas cher
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            messages.append(response_message)
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "lire_tarifs": function_response = lire_tarifs()
                elif function_name == "consulter_stock": function_response = consulter_stock()
                elif function_name == "prendre_rendez_vous":
                    function_response = prendre_rendez_vous(
                        function_args.get("nom_client"),
                        function_args.get("date_heure"),
                        function_args.get("objet")
                    )
                
                messages.append({
                    "tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": function_response
                })
            
            second_response = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
            return jsonify({"reply": second_response.choices[0].message.content})
        else:
            return jsonify({"reply": response_message.content})

    except Exception as e:
        return jsonify({"reply": f"Désolé, je rencontre une erreur technique. ({e})"}), 500

# Route pour afficher votre site web
@app.route('/')
def index():
    return send_from_directory(DOSSIER_ACTUEL, 'index.html')

if __name__ == '__main__':
    # Render utilise la variable d'environnement PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)