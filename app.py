from flask import Flask, render_template, request, jsonify, session
import json
from difflib import SequenceMatcher
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# Load the knowledge base
def load_knowledge_base():
    try:
        with open('knowledge_base.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return {'symptoms': []}

knowledge_base = load_knowledge_base()

# Translations dictionary
translations = {
    "en": {
        "greeting": "Hello! I'm your medical assistant. Please describe your symptoms, and I'll recommend appropriate medicine.",
        "no_match": "No matching conditions found. Try rephrasing or consult a healthcare professional.",
        "found_recommendations": "I found {count} recommendation(s) for you:",
        "error": "Sorry, there was an error. Please try again."
    },
    "fr": {
        "greeting": "Bonjour! Je suis votre assistant médical. Veuillez décrire vos symptômes et je vous recommanderai un médicament approprié.",
        "no_match": "Aucune condition correspondante trouvée. Essayez de reformuler ou consultez un professionnel de la santé.",
        "found_recommendations": "J'ai trouvé {count} recommandation(s) pour vous:",
        "error": "Désolé, une erreur s'est produite. Veuillez réessayer."
    },
    "ar": {
        "greeting": "مرحبا! أنا مساعدك الطبي. يرجى وصف الأعراض الخاصة بك، وسأوصي بالدواء المناسب.",
        "no_match": "لم يتم العثور على حالات مطابقة. حاول إعادة الصياغة أو استشر أخصائي الرعاية الصحية.",
        "found_recommendations": "لقد وجدت {count} توصية لك:",
        "error": "عذرا، حدث خطأ. يرجى المحاولة مرة أخرى."
    },
    "darija": {
        "greeting": "السلام! أنا المساعد الطبي ديالك. قول لي شنو كتحس بيه، وغادي نقترح عليك الدوا المناسب.",
        "no_match": "ما لقيناش شي حاجة مطابقة. حاول تعاود تقول بشكل آخر أو مشي عند طبيب.",
        "found_recommendations": "لقيت ليك {count} توصية:",
        "error": "سماح، وقع شي غلط. عاود حاول."
    }
}

# String similarity
def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Find matching medical conditions
def find_medicine(user_symptoms):
    user_symptoms = user_symptoms.lower().strip()
    scored_matches = []

    for symptom_data in knowledge_base['symptoms']:
        score = 0
        matched_keywords = []

        # Exact keyword matches
        for keyword in symptom_data['keywords']:
            if keyword in user_symptoms:
                score += 10
                matched_keywords.append(keyword)

        # Fuzzy matching
        for word in user_symptoms.split():
            for keyword in symptom_data['keywords']:
                sim = similarity(word, keyword)
                if sim > 0.8 and keyword not in matched_keywords:
                    score += sim * 5
                    matched_keywords.append(keyword)

        # If something matched → keep it
        if score > 0:
            symptom_copy = symptom_data.copy()
            symptom_copy["match_score"] = score
            symptom_copy["matched_keywords"] = matched_keywords
            scored_matches.append(symptom_copy)

    # Sort by match score (best first)
    scored_matches.sort(key=lambda x: x["match_score"], reverse=True)

    # Return top 5 matches
    return scored_matches[:5]


@app.route('/')
def home():
    # Initialize session if not exists
    if 'chat_history' not in session:
        session['chat_history'] = []
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')


@app.route('/get_recommendation', methods=['POST'])
def get_recommendation():
    data = request.get_json()
    user_input = data.get('symptoms', '')
    language = data.get('language', 'en')

    if not user_input or len(user_input.strip()) < 3:
        return jsonify({'error': 'Please describe your symptoms (at least 3 characters)'})

    # Initialize chat history if not exists
    if 'chat_history' not in session:
        session['chat_history'] = []

    # Add user message to history
    session['chat_history'].append({
        'role': 'user',
        'message': user_input,
        'timestamp': str(uuid.uuid4())
    })

    recommendations = find_medicine(user_input)

    if recommendations:
        # Add bot response to history
        session['chat_history'].append({
            'role': 'bot',
            'message': translations[language]['found_recommendations'].format(count=len(recommendations)),
            'recommendations': recommendations,
            'timestamp': str(uuid.uuid4())
        })
        session.modified = True
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'message': translations[language]['found_recommendations'].format(count=len(recommendations))
        })
    else:
        # Add bot response to history
        session['chat_history'].append({
            'role': 'bot',
            'message': translations[language]['no_match'],
            'timestamp': str(uuid.uuid4())
        })
        session.modified = True
        
        return jsonify({
            'success': False,
            'message': translations[language]['no_match']
        })


@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    """Returns chat history for the current session"""
    if 'chat_history' not in session:
        session['chat_history'] = []
    return jsonify({'history': session.get('chat_history', [])})


@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Clears chat history"""
    session['chat_history'] = []
    session.modified = True
    return jsonify({'success': True})


@app.route('/get_all_conditions', methods=['GET'])
def get_all_conditions():
    """Returns all condition names for autocomplete"""
    conditions = [symptom['condition'] for symptom in knowledge_base['symptoms']]
    return jsonify({'conditions': conditions})


@app.route('/get_translation', methods=['POST'])
def get_translation():
    """Returns translation for a given key and language"""
    data = request.get_json()
    language = data.get('language', 'en')
    key = data.get('key', 'greeting')
    return jsonify({'translation': translations.get(language, translations['en']).get(key, '')})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)