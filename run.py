import argparse

from maildump import app, start


parser = argparse.ArgumentParser()
parser.add_argument('--smtp-ip', default='127.0.0.1')
parser.add_argument('--smtp-port', default=1025, type=int)
parser.add_argument('--http-ip', default='127.0.0.1')
parser.add_argument('--http-port', default=1080, type=int)
parser.add_argument('--db', help='SQLite database - in-memory if missing')
parser.add_argument('-f', '--foreground', help='Run in the foreground', action='store_true')
parser.add_argument('-d', '--debug', help='Run the web app in debug mode', action='store_true')
args = parser.parse_args()

app.debug = args.debug
start(args.http_ip, args.http_port, args.smtp_ip, args.smtp_port, args.db)