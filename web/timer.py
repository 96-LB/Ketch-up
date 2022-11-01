import random
from flask_discord import requires_authorization
from flask import abort, render_template, request
from flask_socketio import ConnectionRefusedError, emit
from functools import wraps
from core.web import app, discord, socket
from core.data import Player, Room
from .combat import requires_party_member

def requires_leader(func):
    @wraps(func)
    @requires_party_member
    def wrapper(room, *args, **kwargs):
        if Player(discord.fetch_user().id) != Room(room).get_leader():
            print('♥') # just so it's not TOO silent
            return
        return func(room, *args, **kwargs)
    return wrapper


# start a thread to ping the client
def start_timer(room, minutes, rest=False):
    Room(room).start_timer(minutes, rest)
    


def timer_loop(room):
    while True:
        if not Room(room).is_running():
            return
        socket.emit('timer', Room(room).get_remaining_time(), to=room)
        if Room(room).get_remaining_time() <= 0:
            if Room(room).get_leader() is None:
                Room(room).reset()
                return
            if Room(room).on_break():
                socket.emit('message', 'Back to work!', to=room)
                socket.emit('timer_work', to=room)
                Room(room).start_timer(25)
            else:
                socket.emit('message', 'Break time~!', to=room)
                socket.emit('timer_break', to=room)
                Room(room).clear_turn()
                Room(room).start_timer(5, True)
        socket.sleep(1)



@socket.event
@requires_leader
def start_timer(room):
    if Room(room).is_running():
        return
    
    Room(room).start_timer(25)
    
    if Room(room).get_hp() <= 0:
        Room(room).summon_boss(hp=100, damage=random.randint(20, 30))
    
    
    socket.start_background_task(timer_loop, room)
    socket.emit('timer_start', to=room)
    emit('message', 'It\'s time to Ketch up on your work~!', to=room)