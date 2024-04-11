from flask import Flask, request, jsonify
from financial_module import get_financial_table_summarized
import numpy as np
import pandas as pd
from flask_cors import CORS, cross_origin

app = Flask(__name__)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy   dog'
app.config['CORS_HEADERS'] = 'Content-Type'

cors = CORS(app, resources={r"/*": {"origins": "http://localhost:port"}})

@app.route('/get_financial_table_summarized', methods=['POST', 'OPTIONS'])
@cross_origin(origin='localhost',headers=['Content- Type','Authorization'])

def get_financial_table_summarized_endpoint():
    if request.method == 'OPTIONS':
        # Preflight request. Reply successfully:
        response = flask.jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    
    property_list = request.json['property_list']
    print(property_list)
    try:
        rental_df = get_financial_table_summarized(property_list)
        rental_df = rental_df.replace([np.inf, -np.inf], np.finfo(np.float64).max)
        response = rental_df.to_dict(orient='records') 
        response = jsonify(response)
        return response
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)