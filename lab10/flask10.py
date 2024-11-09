#!/usr/bin/python3
from flask import Flask, request, jsonify

app = Flask(__name__)

def calculate(arg1, op, arg2):
    if op == '+':
        return arg1 + arg2
    elif op == '-':
        return arg1 - arg2
    elif op == '*':
        return arg1 * arg2
    else:
        raise ValueError("Unsupported operator")

@app.route('/<int:arg1>/<string:op>/<int:arg2>', methods=['GET'])
def calculate_get(arg1, op, arg2):
    try:
        result = calculate(arg1, op, arg2)
        return jsonify({"result": result}), 200
    except ValueError:
        return jsonify({"error": "Invalid input"}), 400

@app.route('/', methods=['POST'])
def calculate_post():
    data = request.get_json()
    if not data or 'arg1' not in data or 'op' not in data or 'arg2' not in data:
        return jsonify({"error": "Missing required data"}), 400
    
    try:
        arg1 = int(data['arg1'])
        op = data['op']
        arg2 = int(data['arg2'])
        result = calculate(arg1, op, arg2)
        return jsonify({"result": result}), 200
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid input"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=20201)