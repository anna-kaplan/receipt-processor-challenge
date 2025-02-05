from flask import Flask, request, jsonify
from flask_expects_json import expects_json
import uuid
import math
import datetime

import logging

from config import Config

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M'

schema_patterns = {
    DATE_FORMAT: r"^\d{4}-\d{2}-\d{2}$",
    TIME_FORMAT: r"^\d{2}:\d{2}$"
    }

request_schema = {
    'type': 'object',
    'properties': {
        'retailer': {'type': 'string', 'pattern': r"^[\w\s\-&]+$"},
        'purchaseDate': {'type': 'string', 'pattern': schema_patterns[DATE_FORMAT]},
        'purchaseTime': {'type': 'string', 'pattern': schema_patterns[TIME_FORMAT]},
        'total':  {'type': 'string', 'pattern': r"^\d+\.\d{2}$"},
        'items': {
            'type' : 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'shortDescription': {'type': 'string'},
                    'price': {'type': 'string', 'pattern': r"^\d+\.\d{2}$"}
                },
                'required': ['shortDescription', 'price']
            },
            'minItems': 1  # to ensure at least one item,
        }
    },
    'required': ['retailer', 'purchaseDate', 'purchaseTime', 'total', 'items']
}

receipt_storage = {}  # storage of processed receipts


@app.route('/receipts/process', methods=['POST'])
@expects_json(request_schema)  # verifies json, otherwise returns status_code = 400
def process_receipt():
    try:
        input_data = request.get_json()
        receipt_id = get_new_receipt_id()
        receipt = process_input(input_data)
        # TODO - validate that receipt['purchasedDateTime']
        # - how old can the receipt be? Time is not in the future.
        # timezone?
        receipt['points'] = calculate_points(receipt)
        save_receipt(receipt_id, receipt)
        logging.info(f'Processed receipt, id={receipt_id}')

        return jsonify({'id': receipt_id}), 200
    except Exception as e:
        message = f'An error occured during receipt processing - {e}'
        logging.error(message)
        return jsonify({'message': message}), 500


@app.route('/receipts/<receipt_id>/points', methods=['GET'])
def get_points(receipt_id):
    receipt = receipt_storage.get(receipt_id)
    if receipt:
        return jsonify({'points': receipt['points']}), 200
    else:
        return jsonify({'message': f'No receipt found with ID={receipt_id}'}), 404


def get_new_receipt_id():
    """
    Generates UUID for a receipt
    :returns: string of generated UUID
    """
    new_id = uuid.uuid4()
    if new_id in receipt_storage:
        return get_new_receipt_id()
    return str(new_id)


def save_receipt(receipt_id, receipt):
    """appends receipts to receipt_storage
    """
    receipt_storage[receipt_id] = receipt


def process_input(data):
    """
    :param data: object from request with the defined schema "request_schema"
    :returns: receipt object composed from elements of input data
    """
    return {
        'retailer': data['retailer'],
        'total': float(data['total']),

        'purchaseDateTime': datetime.datetime.strptime(
            data['purchaseDate'] + ' ' + data['purchaseTime'],
            f'{DATE_FORMAT} {TIME_FORMAT}'),

        'items': [{'shortDescription': elem['shortDescription'], 'price': float(elem['price'])}
                  for elem in data['items']]
    }


def calculate_points(receipt):
    """
    Calculates points from the receipt data
    :params: receipt object
    :returns: points value in int
    """
    parse_point_rules = {
        'retailer_alnum': sum(1 for char in receipt['retailer'] if char.isalnum()),
        'total_round_dollar': 50 if receipt['total'] % 1 == 0 else 0,
        'total_in_quarters': 25 if receipt['total'] * 100 % 25 == 0 else 0,
        'each_pair_of_items_5c': 5 * (len(receipt['items']) // 2),
        'items_names_in3': sum([math.ceil(0.2 * item['price']) for item in receipt['items']
                                if len(item['shortDescription'].strip()) % 3 == 0
                                ]),
        'odd_day': 6 if receipt['purchaseDateTime'].day % 2 else 0,
        'special_time': 10 if 14 <= receipt['purchaseDateTime'].hour < 16 else 0
    }

    return sum(parse_point_rules.values())


if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT)
