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


from imp import reload  # py2/3; needed cuz reload used on utils

import sys, time, re
from os.path import dirname, abspath

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from mycroft.messagebus.message import Message

sys.path.append(abspath(dirname(__file__)))  # local imports hack

try:
    reload(utils)

except NameError:
    import utils

for name in dir(utils):
    # unpack
    if not '__' in name:
        if eval('"{}" in globals()'.format(name)): exec('del {}'.format(name))
        exec('{0} = getattr(utils, "{0}")'.format(name))

try:
    reload(abilities)

except NameError:
    import abilities


__author__ = 'skeledrew'
__version__ = '0.3.1'


class MathSkill(MycroftSkill):

    def __init__(self):
        super(MathSkill, self).__init__(name='MathSkill')
        self.h_prefix = 'Dyn'
        self.bridged_funcs = {}
        self.Message = Message
        self.waiting = True
        self.thot_chains = {}
        self.create_skill_ref = create_skill
        self.alerts = []

    def initialize(self):
        #announce_rx = 'announce (?P<Words>.*)'
        #self.add_ability(announce_rx, self.handle_announce_intent)
        #self.add_ability('brain scan', self.handle_scan_intent)
        self.add_ability('reload abilities', self.reload_abilities)
        #grep_log_rx = 'search skill log for (?P<Search>.*)'#( and )?(?P<Before>\d*)( before )?( and )?(?P<After>\d*)( after)?'
        #self.add_ability(grep_log_rx, self.handle_grep_log_intent)
        self.load_abilities()
        #if not 'thot_chains' in self.settings: self.settings['thot_chains'] = {}
        self.load_chains()
        #self.emitter.on('recognizer_loop:audio_output_end', self.ready_to_continue)

    def add_ability(self, rx, handler):
        self.log.info('Binding "{}" to "{}"'.format(rx, repr(handler)))
        intents = self.make_intents_struct(rx)

        while intents:
            intent = intents.pop()

            try:
                self.register_intent(intent, handler)

            except Exception as e:
                self.log.error('Failed to bind {} to {}: {}. Skipped...'.format(intent, handler.__name__, repr(e)))

    def reload_abilities(self, msg):
        reload(abilities)
        self.load_abilities()
        self.load_chains()
        self.speak('abilities reloaded!')

    def load_abilities(self):
        # load core and pipes
        self.missing_abilities = []

        for abl_name in dir(abilities):
            # core abilities
            #if '__' in abl_name or abl_name in dir(utils): continue
            if not abl_name.startswith('abl_'): continue
            abl = getattr(abilities, abl_name)
            if not 'function' in repr(abl): continue
            rx = abl()
            if not isinstance(rx, str) or not rx: continue
            try:
                self.add_ability(rx, self.handle_external_intent)
                self.bridged_funcs[rx] = abl

            except Exception as e:
                self.missing_abilities.append([abl_name, str(e.args)])

    def handle_external_intent(self, msg):
        # bridge to function
        #self.log.debug('bridging; m_data = {}'.format(repr(msg.data)))
        ext_func = None
        utt = msg.data.get('utterance')

        for rx in self.bridged_funcs:
            match = 'True' if rx == utt else 'False'
            self.log.debug('searching for correct bridge; rx = {}; utt = {}; match = {}'.format(rx, utt, match))
            if not re.match(rx, utt): continue
            ext_func = self.bridged_funcs[rx]
            break
        if not ext_func:
            self.log.error('Failed to resolve "{}" to an external action.'.format(utt))
            return False
        ext_func(self, msg)
        return True

    def load_chains(self):
        self.thot_chains = self.settings['thot_chains']
        #self.log.debug('All chains = {}'.format(str(self.thot_chains)))

        for chain in self.thot_chains:
            # chained abilities
            self.log.info('Adding chain "{}" of type = {}'.format(chain, type(chain)))
            if not isinstance(chain, str): continue  # unicode instead of str for Py2 compat
            self.add_ability(chain, self.handle_chain_intent)

    def handle_chain_intent(self, msg):
        # bridge to loaded chain
        chain = None
        utt = msg.data.get('utterance')

        for ch_name in self.thot_chains:
            match = 'True' if ch_name == utt else 'False'
            self.log.debug('searching for correct chain; chain name = {}; utt = {}; match = {}'.format(ch_name, utt, match))
            if not re.match(ch_name, utt): continue
            chain = self.thot_chains[ch_name]
            break
        self.exec_chain(chain)

    def handle_announce_intent(self, msg):
        words = msg.data.get('Words')
        self.speak(words)

    def converse(self, utts, lang='en-us'):
        result = False

        for utt in utts:
            msg = Message('', {"lang": lang, "utterance": utts})
            result = self.handle_external_intent(msg)
            if result: break
        return result

    def make_intents(self, rx):
        rx_combos = [rx]
        rx_combos = expand_rx(rx.strip())
        intents = []
        if interact: pdb.set_trace()

        for combo in rx_combos:
            i_name = '{}{}Intent'.format(self.h_prefix, hash_sum(combo))
            #self.log.debug('combo = {}'.format(combo))

            if re.match('^[a-z0-9 ]+$', combo):
                # keywords only
                entity_type = self.make_entity_type(combo)
                intent = IntentBuilder(re.sub('Keywords?', 'Intent', entity_type)).require(entity_type).build()
                intents.append(intent)
                continue
            self.register_regex(combo)
            parts = re.split('(\(|\))', combo)
            intent_builder = IntentBuilder(i_name)
            section = ''

            for idx in range(len(parts)):
                # separate keywords from names
                part = parts[idx]

                if section and part == '(':
                    # got a complete keyword
                    entity_type = self.make_entity_type(section)
                    intent_builder.require(entity_type)
                    section = '('
                    continue
                section += part
                match = re.match('\(\?P<\w+>.+\)', section)

                if match:
                    # got a named group
                    span = re.search('<\w+>', section).span()
                    entity_type = section[span[0]+1:span[1]-1]

                    if not idx == len(parts) - 1 and re.match('(\?|\*).*', parts[idx + 1]):
                        intent_builder.optionally(entity_type)

                    else:
                        intent_builder.require(entity_type)
                    section = ''
                    continue
            intents.append(intent_builder.build())
            self.log.info('Created intent: {}'.format(str(intents[-1].__dict__)))
        return intents

    def make_intents_struct(self, struct_list):
        # process new style intent for i18n
        intents = []

        for struct in struct_list:
            # single language

            for i_inf in struct['utterances']:
                # intent info
                i_name = '{}{}Intent'.format(self.h_prefix, hash_sum(str(i_inf)))
                builder = IntentBuilder(i_name)

                for section in i_inf:
                    section = ''.join(ch for ch in section if re.match(r'A-Za-z0-9:\|', ch))
                    entity_type = self.make_entity_type(section.split(':')[1])

                    if section.startswith('req:'):
                        builder.require(entity_type)
                        continue

                    elif section.startswith('opt:'):
                        builder.optionally(entity_type)
                        continue

                    elif section.startswith('one:'):
                        entity_types = [self.make_entity_type(e) for e in section.split(':')[1].split('|')]
                        builder.one_of(entity_types)
                        continue

                    else:
                        # shouldn't be here
                        self.log.error('Something wrong with the struct: {}'.format(struct))
                intents.append(builder.build())
        return intents

    def make_entity_type(self, entity):
        entity = entity.strip()
        entity_type = ''.join(entity.title().split(' ')) + 'Keyword' + ('s' if ' ' in entity else '')
        self.register_vocabulary(entity, entity_type)
        return entity_type

    def ready_to_continue(self):
        self.log.debug('Ready event detected')
        self.waiting = False

    def exec_chain(self, chain):

        for link in chain:
            self.waiting = True

            if isinstance(link, dict):
                abilities.whisper(self, link)

            elif isinstance(link, list) and link[0] == 'whisper':
                abilities.whisper(self, link[1])

            else:
                abilities.shout(self, link[1])
            timeout = 0

            while self.waiting and timeout < 10:
                time.sleep(1)
                timeout += 1

    def alert(self, text, details):
        self.alerts.append(text)
        self.enclosure.mouth_text('ALERT DETECTED')
        self.log.info('!!!ALERT DETECTED!!! {} -- {}'.format(text, details))

def create_skill():
    return MathSkill()


if sys.argv[0] == '' and not __name__ == '__main__':
    interact = True # for pdb trace activation
