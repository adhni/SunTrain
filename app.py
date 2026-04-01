from dashboard.app import app, server


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
