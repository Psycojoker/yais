import asyncio

class IRCServer():
    def __init__(self):
        self.users = []
        self.tasks_to_user = {}

    def client_connected_handler(self, reader, writer):
        print("New user")
        user = User(reader, writer)
        self.users.append(user)

        task = asyncio.Task(self.user_loop(user))
        self.tasks_to_user[task] = user
        task.add_done_callback(self.client_connected_done)

    @asyncio.coroutine
    def user_loop(self, user):
        try:
            data = (yield from user.reader.readline())
            print(data)
            proto, nick = data.rstrip().split()
            assert proto == b"NICK"
            user.nick = nick
            data = (yield from user.reader.readline())
            print(data)
            proto, realname = data.rstrip().split(b" ", 1)
            assert proto == b"USER"
            user.writer.write((":%s MODE %s :+i\r\n" % (nick, nick)).encode("Utf-8"))

            user.writer.write(b":myself 001 " + nick + b" :Hello honey\r\n")
            user.writer.write(b":myself 002 " + nick + b" :foo\r\n")
            user.writer.write(b":myself 003 " + nick + b" :bar\r\n")
            user.writer.write(b":myself 004 " + nick + b" :baz\r\n")
            while True:
                data = (yield from user.reader.readline())
                if not data:
                    continue
                print("%s: %s" % (user, data))

                command, data = data.split(b" ", 1)

                if command == b"PING":
                    user.writer.write(b"PONG " + data + b"\r\n")

        except Exception as e:
            import traceback, sys
            traceback.print_exc(file=sys.stdout)
            print(e)

    def client_connected_done(self, task):
        user = self.tasks_to_user[task]
        self.users.remove(user)


class User():
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.nick = None


loop = asyncio.get_event_loop()
server = asyncio.start_server(IRCServer().client_connected_handler, 'localhost', 1234)
server = loop.run_until_complete(server)

try:
    loop.run_forever()
finally:
    loop.close()
