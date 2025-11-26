from flask import Flask
import os
import facebook_scraper  # rename this to your real script file

app = Flask(__name__)

@app.route("/")
def run():
    facebook_scraper.check_for_promotions()   # call your scraping function
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port)