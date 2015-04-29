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
            data = yield from self.get_next_line()

            proto, nick = data.rstrip().split()
            assert proto == "NICK"
            self.nick = nick

            data = yield from self.get_next_line()

            proto, realname = data.rstrip().split(" ", 1)
            assert proto == "USER"
            self.send(":%s MODE %s :+i" % (nick, nick))

            self.send_motd()

            while True:
                data = yield from self.get_next_line()
                self.debug(data)

                command, data = data.split(" ", 1)

                if command == "PING":
                    self.send("PONG " + data)

        except Exception as e:
            import traceback, sys
            traceback.print_exc(file=sys.stdout)
            self.debug(e)

    @asyncio.coroutine
    def get_next_line(self):
        data = (yield from self.reader.readline())
        while not data:
            data = (yield from self.reader.readline())

        self.debug(data.decode("Utf-8"))
        return data.decode("Utf-8")

    def debug(self, data):
        if isinstance(data, bytes):
            print("%s -> %s" % (self.nick if self.nick else id(self), data.decode("Utf-8").rstrip()))
        else:
            print("%s -> %s" % (self.nick if self.nick else id(self), data.rstrip()))

    def send(self, data):
        if isinstance(data, bytes):
            if not data.endswith(b"\r\n"):
                data += b"\r\n"

            print("%s <- %s" % (self.nick, data.decode("Utf-8").rstrip()))
            self.writer.write(data)

        else:
            if not data.endswith("\r\n"):
                data += "\r\n"

            print("%s <- %s" % (self.nick, data.rstrip()))
            self.writer.write(data.encode("Utf-8"))

    def send_motd(self):
        self.send(":myself 001 %s :Hello honey" % self.nick)
        self.send(":myself 002 %s :foo" % self.nick)
        self.send(":myself 003 %s :bar" % self.nick)
        self.send(":myself 004 %s :baz" % self.nick)


loop = asyncio.get_event_loop()
print("Starting server...")
server = asyncio.start_server(IRCServer().client_connected_handler, 'localhost', 1234)
server = loop.run_until_complete(server)

try:
    loop.run_forever()
finally:
    loop.close()
