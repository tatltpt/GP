from flaskblog import app

if __name__ == '__main__':
    # socketio.run(app, host='0.0.0.0', port=5555, debug=True)
    app.run(host='0.0.0.0', port=5555, debug=True)
