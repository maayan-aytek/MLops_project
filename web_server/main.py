from website.app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # app.run(host='192.168.1.21', port=5000, debug=True)
    # socketio.run(app, debug=True)
    socketio.run(app, debug=True, host='0.0.0.0', port=5050, use_reloader=False)
    # socketio.run(app, debug=True, host='0.0.0.0', port=5050, use_reloader=False, async_mode='eventlet')