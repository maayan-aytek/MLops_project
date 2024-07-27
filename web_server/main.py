from website.app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='10.0.0.6', port=5000, debug=True)
