import waitress
from Portfolio.wsgi import application

if __name__ == "__main__":
    waitress.serve(
        application,
        host="127.0.0.1",
        port=8030,
        threads=4
    )