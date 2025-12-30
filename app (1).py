from flask import Flask, request, jsonify
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dateutil.parser import parse
from datetime import datetime, timedelta

# ================== CONFIG ==================
API_TOKEN = "SECRET_TOKEN_123"
SPREADSHEET_NAME = "Currency_update"
NBU_API_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange"

# Google auth
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
CREDS_FILE = "/home/4asdfcv/mysite/credentials.json"

# ============================================

app = Flask(__name__)


def get_google_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    return sheet

def fetch_rates(date):
    params = {
        "date": date.strftime("%Y%m%d"),
        "json": ""
    }
    response = requests.get(NBU_API_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

@app.route("/update_rates", methods=["GET"])
def update_rates():

    token = request.args.get("token")
    if token != API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    update_from = request.args.get("update_from")
    update_to = request.args.get("update_to")

    try:
        start_date = parse(update_from).date() if update_from else datetime.today().date()
        end_date = parse(update_to).date() if update_to else datetime.today().date()
    except Exception:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if start_date > end_date:
        return jsonify({"error": "update_from > update_to"}), 400


    all_rows = []
    current_date = start_date

    while current_date <= end_date:
        try:
            rates = fetch_rates(current_date)
            for r in rates:

                if r["cc"] == "USD":
                    all_rows.append([
                        current_date.strftime("%Y-%m-%d"),
                        r["cc"],
                        r["rate"]
                    ])
        except Exception as e:

            print(f"Error fetching for {current_date}: {e}")

        current_date += timedelta(days=1)

    if all_rows:
        try:
            sheet = get_google_sheet()

            sheet.append_rows(all_rows)
        except Exception as e:
            return jsonify({"error": f"Google Sheets API error: {str(e)}"}), 500

    return jsonify({
        "status": "success",
        "added_rows": len(all_rows),
        "from": start_date.isoformat(),
        "to": end_date.isoformat()
    })

if __name__ == "__main__":
    app.run()