# This file is part of math-skill

# math-skill - This is a Mycroft skill that is intended to be dynamically extensible and modifiable.

# @author Andrew Phillips
# @copyright 2017 Andrew Phillips <skeledrew@gmail.com>

# math-skill is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.

# math-skill is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.

# You should have received a copy of the GNU Affero General Public
# License along with math-skill.  If not, see <http://www.gnu.org/licenses/>.


from utils import unicode_literals, bytes, str, reload

import re
import time
import sys

import pexpect

missing_modules = []

from mycroft.messagebus.message import Message

try:
    reload(mycroftbss)

except NameError:
    try:
        import mycroftbss  # https://github.com/skeledrew/mcbss

    except Exception:
        missing_modules.append('mycroft brain skill services')

state = None

class State():

    def __init__(self):
        self.host_info = utils.str_to_dict(pexpect.run("/bin/sh -c 'cat /etc/*-release'").decode(), '\r\n', '=')


def blank(this=None, msg=None):
    if not this: return 'ability template'
    this.speak('Please copy this template to make your own abilities')

def check_imports(this=None, msg=None):
    if not this: return None
    return missing_modules

def whisper(this=None, msg=None):
    try:
        return mycroftbss.whisper(this, msg)
    except Exception as e:
        return e

def shout(this=None, utterances=None):
    try:
        return mycroftbss.shout(this, utterances)
    except Exception as e:
        return e

def check_condition(this=None, msg=None):
    # emulate if-then-else
    if not this: return 'check if (?P<Condition>.+) then (?P<TrueAction>.+)( otherwise)? (?P<FalseAction>.+)?'
    condition = msg.data.get('Condition')
    true_action = msg.data.get('TrueAction')
    false_action = msg.data.get('FalseAction', None)
    which_action = process_condition(condition)
    if which_action == None: return False
    chosen_action = true_action if which_action else false_action if false_action else None
    if not chosen_action: return True
    comm_type = whisper if chosen_action.startswith('call intent') else shout
    comm_type(this, chosen_action)
    return True

def process_condition(condition=None):
    if not condition: return None  # prevent register
    return

def abl_activate(this=None, msg=None):
    # prioritize skill for upcoming commands; start convo?; move
    if not this: return [{'utterances': [['req:activate calculator']]}]
    this.speak('Calculator activated', True)
    return True

def abl_calculate(this=None, msg=None):
    if not this: return [{'lang': 'en-us', 'utterances': [['req:calculate', 'req:(?P<What>.+)']]}]
    what = msg.data.get('What')

def abl_add(this=None, msg=None):
    if not this: return [{'lang': 'en-us', 'utterances': [['req:what is', 'req:(?P<Number1>\d+)', 'req:plus', 'req:(?<Number2>\d+)', 'opt:(?P<Rest>.*)'], ['req:add', 'req:(?P<Number1>\d+)', 'one:and|to', 'req:(?<Number2>\d+)', 'opt:(?P<Rest>.*)']]}]
    numbers = []
    numbers = [int(msg.data.get('Number1')), int(msg.data.get('Number2'))]
    # TODO: parse Rest and include
    result = sum_these(numbers)
    this.speak(result)
def sum_these(nums):
    # takes any amount of numbers in a list
    return sum(nums)

if sys.argv[0] == '' and not __name__ == '__main__':
    # running as imported module
    global state
    state = State()
