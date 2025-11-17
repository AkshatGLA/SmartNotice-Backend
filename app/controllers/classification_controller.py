from flask import Blueprint, request, jsonify
from flask_cors import CORS
import torch
import joblib
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from ..middleware.auth_middleware import token_required

classification_bp = Blueprint('classification', __name__, url_prefix='/api')
CORS(classification_bp)

# Get absolute path to the model directory
current_dir = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.abspath(os.path.join(current_dir, '../models/classification-model'))

# Verify the model directory exists
if not os.path.exists(MODEL_DIR):
    raise FileNotFoundError(f"Model directory not found at: {MODEL_DIR}")

# Verify required files exist (updated for safetensors format)
required_files = ['config.json', 'model.safetensors', 'special_tokens_map.json', 
                 'tokenizer_config.json', 'tokenizer.json', 'vocab.txt', 'label_encoder.pkl']
for file in required_files:
    if not os.path.exists(os.path.join(MODEL_DIR, file)):
        raise FileNotFoundError(f"Required file {file} not found in model directory")

try:
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    
    # Load model - explicitly specify safetensors format
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_DIR,
        local_files_only=True,
        use_safetensors=True  # Important for safetensors format
    )
    model.eval()
    
    # Load label encoder
    label_encoder = joblib.load(os.path.join(MODEL_DIR, 'label_encoder.pkl'))
except Exception as e:
    raise RuntimeError(f"Failed to load model components: {str(e)}")

@classification_bp.route('/classify', methods=['POST'])
@token_required
def classify_text(current_user):
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Invalid or missing 'text' in JSON payload"}), 400

    text = data.get("text", "")
    
    try:
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512
        )

        with torch.no_grad():
            outputs = model(**inputs)
            predicted_class = torch.argmax(outputs.logits, dim=1).item()

        label = label_encoder.inverse_transform([predicted_class])[0]
        return jsonify({"category": label}), 200
    except Exception as e:
        return jsonify({"error": f"Classification failed: {str(e)}"}), 500