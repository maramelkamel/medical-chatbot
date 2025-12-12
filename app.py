from flask import Flask, render_template, request, jsonify
import json
from difflib import SequenceMatcher

app = Flask(__name__)

# Load the knowledge base
def load_knowledge_base():
    try:
        with open('knowledge_base.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return {'symptoms': []}

knowledge_base = load_knowledge_base()

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
    return render_template('index.html')


@app.route('/get_recommendation', methods=['POST'])
def get_recommendation():
    data = request.get_json()
    user_input = data.get('symptoms', '')

    if not user_input or len(user_input.strip()) < 3:
        return jsonify({'error': 'Please describe your symptoms (at least 3 characters)'})

    recommendations = find_medicine(user_input)

    if recommendations:
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No matching conditions found. Try rephrasing or consult a healthcare professional.'
        })


@app.route('/get_all_conditions', methods=['GET'])
def get_all_conditions():
    """Returns all condition names for autocomplete"""
    conditions = [symptom['condition'] for symptom in knowledge_base['symptoms']]
    return jsonify({'conditions': conditions})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
