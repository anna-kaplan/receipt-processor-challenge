import unittest
from flask import json
import datetime

from receipt_api import calculate_points, process_input, app, receipt_storage

valid_receipt = {
    "retailer": "Walgreens",
    "purchaseDate": "2022-01-02",
    "purchaseTime": "08:13",
    "total": "2.65",
    "items": [
        {"shortDescription": "Pepsi - 12-oz", "price": "1.25"},
        {"shortDescription": "Dasani", "price": "1.40"}
    ]
}

class ReceiptProcessingTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.receipt_storage = receipt_storage
        self.receipt_storage.clear()

    def test_process_input(self):
        result = process_input(valid_receipt)
        self.assertEqual(result['retailer'], valid_receipt['retailer'])
        self.assertEqual(result['total'], float(valid_receipt['total']))

        date_time_string = f"{valid_receipt['purchaseDate']} {valid_receipt['purchaseTime']}"
        self.assertEqual(result['purchaseDateTime'],
                         datetime.datetime.strptime(date_time_string, "%Y-%m-%d %H:%M"))

        self.assertEqual(len(result['items']), len(valid_receipt['items']))
        self.assertEqual([r['shortDescription'] for r in result['items']],
                         [p['shortDescription'] for p in valid_receipt['items']])
        self.assertEqual([r['price'] for r in result['items']],
                         [float(p['price']) for p in valid_receipt['items']])

    def test_calculate_points(self):
        recipt_data = {
            "retailer": "Target",
            "purchaseDate": "2022-01-01",
            "purchaseTime": "13:01",
            "items": [
                {"shortDescription": "Mountain Dew 12PK", "price": "6.49"},
                {"shortDescription": "Emils Cheese Pizza", "price": "12.25"},
                {"shortDescription": "Knorr Creamy Chicken", "price": "1.26"},
                {"shortDescription": "Doritos Nacho Cheese", "price": "3.35"},
                {"shortDescription": "   Klarbrunn 12-PK 12 FL OZ  ", "price": "12.00" }
                ],
            "total": "35.35"
            }
        result = calculate_points(process_input(recipt_data))
        self.assertEqual(result, 28)

    def test_calculate_points_multiple_of_25_daytime(self):
        receipt_data = {
            "retailer": "Target",
            "purchaseDate": "2022-01-01",
            "purchaseTime": "15:01",
            "items": [
                {"shortDescription": "Mountain Dew 12PK", "price": "6.49"},
                {"shortDescription": "Emils Cheese Pizza", "price": "12.25"},
                {"shortDescription": "Knorr Creamy Chicken", "price": "1.26"},
                {"shortDescription": "Doritos Nacho Cheese", "price": "3.00"},
                {"shortDescription": "   Klarbrunn 12-PK 12 FL OZ  ", "price": "12.00" }
                ],
            "total": "35.00"
            }
        receipt = process_input(receipt_data)
        points = calculate_points(receipt)
        self.assertEqual(points, 113)

    def test_process_receipt_valid_input(self):
        response = self.app.post('/receipts/process', json=valid_receipt)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('id', data)
        receipt_id = data['id']
        self.assertIn(receipt_id, self.receipt_storage)
        self.assertEqual(self.receipt_storage[receipt_id]['points'], 15)

        points_response = self.app.get(f'/receipts/{receipt_id}/points')
        self.assertEqual(points_response.status_code, 200)
        data = json.loads(points_response.data)
        self.assertEqual(data, {'points': 15})

    def test_process_receipt_invalid_retailer(self):
        invalid_receipt = {
            "retailer": "Target!",  # Invalid character
            "purchaseDate": "2023-10-27",
            "purchaseTime": "15:30",
            "total": "2.50",
            "items": [{"shortDescription": "Mu-Mu", "price": "2.50"}]
        }
        response = self.app.post('/receipts/process', json=invalid_receipt)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('Target!' in response.data.decode('utf-8'))

    def test_process_receipt_invalid_total_format(self):
        invalid_receipt = {
            "retailer": "Target",
            "purchaseDate": "2023-10-27",
            "purchaseTime": "15:30",
            "total": "25.755",  # Invalid format
            "items": [{"shortDescription": "Mu-Mu", "price": "2.755"}]
        }
        response = self.app.post('/receipts/process', json=invalid_receipt)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('total' in response.data.decode('utf-8'))

    def test_get_points_invalid_id(self):
        response = self.app.get('/receipts/invalid_id/points')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'No receipt found for that ID.')


if __name__ == '__main__':
    unittest.main()