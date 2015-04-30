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


class Chan():
    def __init__(self, name):
        self.name = name


class User():
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.nick = None

    @asyncio.coroutine
    def loop(self):
        try:
            data = yield from self.get_next_line()

            proto, nick = data.split()
            assert proto == "NICK"
            self.nick = nick

            data = yield from self.get_next_line()

            proto, realname = data.split(" ", 1)
            assert proto == "USER"
            self.send(":%s MODE %s :+i" % (nick, nick))

            self.send_motd()

            while True:
                data = yield from self.get_next_line()

                command, data = data.split(" ", 1)

                try:
                    if hasattr(self, "on_%s" % command):
                        getattr(self, "on_%s" % command)(data)
                    else:
                        self.debug("UKNOWN COMMAND: %s %s" % (command, data))
                except Exception as e:
                    import traceback, sys
                    traceback.print_exc(file=sys.stdout)
                    self.debug(e)

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
        return data.decode("Utf-8").rstrip()

    def debug(self, data):
        if isinstance(data, bytes):
            print("%s -> %s" % (self.nick if self.nick else id(self), data.decode("Utf-8").rstrip()))
        else:
            print("%s -> %s" % (self.nick if self.nick else id(self), data.rstrip() if hasattr(data, "rstrip") else data))

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

    def on_PING(self, data):
        self.send("PONG " + data)

    def on_NICK(self, data):
        # XXX should be send to *all* users that know this nick
        # TODO nick collision
        self.send(":%s NICK %s" % (self.nick, data))
        self.nick = data

    def on_JOIN(self, data):
        # XXX should be send to *all* users on that chan
        # FIXME a chan can't start with a [a-zA-Z]
        self.send(":%s JOIN %s" % (self.nick, data))

    def on_PRIVMSG(self, data):
        target, content = data.split(" :", 1)
        # TODO send message to target
        pass


loop = asyncio.get_event_loop()
print("Starting server...")
server = asyncio.start_server(IRCServer().client_connected_handler, 'localhost', 1234)
server = loop.run_until_complete(server)

try:
    loop.run_forever()
finally:
    loop.close()
