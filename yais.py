import asyncio

class IRCServer():
    def __init__(self):
        self.users = []
        self.tasks_to_user = {}

    def client_connected_handler(self, reader, writer):
        print("New user")
        user = User(reader, writer)
        self.users.append(user)

        task = asyncio.Task(user.loop())
        self.tasks_to_user[task] = user
        task.add_done_callback(self.client_connected_done)

    def client_connected_done(self, task):
        user = self.tasks_to_user[task]
        self.users.remove(user)


class User():
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.nick = None

    @asyncio.coroutine
    def loop(self):
        try:
            data = (yield from self.reader.readline())
            print(data)
            proto, nick = data.rstrip().split()
            assert proto == b"NICK"
            self.nick = nick
            data = (yield from self.reader.readline())
            print(data)
            proto, realname = data.rstrip().split(b" ", 1)
            assert proto == b"USER"
            self.send(":%s MODE %s :+i" % (nick, nick))

            self.send(":myself 001 %s :Hello honey" % nick)
            self.send(":myself 002 %s :foo" % nick)
            self.send(":myself 003 %s :bar" % nick)
            self.send(":myself 004 %s :baz" % nick)

            while True:
                data = (yield from self.reader.readline())
                if not data:
                    continue
                print("%s: %s" % (id(self), data))

                command, data = data.split(b" ", 1)

                if command == b"PING":
                    self.writer.write(b"PONG " + data + b"\r\n")

        except Exception as e:
            import traceback, sys
            traceback.print_exc(file=sys.stdout)
            print(e)

    def send(self, data):
        if isinstance(data, bytes):
            if not data.endswith(b"\r\n"):
                data += b"\r\n"

            self.writer.write(data)

        else:
            if not data.endswith("\r\n"):
                data += "\r\n"

            self.writer.write(data.encode("Utf-8"))


loop = asyncio.get_event_loop()
print("Starting server...")
server = asyncio.start_server(IRCServer().client_connected_handler, 'localhost', 1234)
server = loop.run_until_complete(server)

try:
    loop.run_forever()
finally:
    loop.close()
