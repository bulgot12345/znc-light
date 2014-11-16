"""A module for ZNC (IRC bouncer software)
Purpose: auto-reply to channel slaps to entertain folks
"""

import znc
import os.path
import random

SPLITTER = ' '

# Our nickname in actions file is substituted with this string
ACTNICK = 'ACTNICK'

class ListStr(list):
    """A list class with modified string representation"""
    def __init__(self, init_str=''):
        super().__init__()
        if init_str != '':
            members = init_str.split(SPLITTER)
            for member in members:
                if member != '':
                    self.append(member)

    def __repr__(self):
        return SPLITTER.join(map(str, self))

    def __str__(self):
        return repr(self)

class slap_ai(znc.Module):
    """Main class for slap_ai functionality"""
    description = "Automated answers for slaps"
    module_types = [znc.CModInfo.UserModule]

    def __init__(self):
        super().__init__()
        self.memos_loaded = False
        # The actual list of actions
        self.actlist = []

    def OnLoad(self, args, message):
        """Auto-executed when the module is loaded in ZNC"""
        # Load users preferences (if defined):
        # accept_channels: channels where we perform (empty = all channels)
        # accept_nick_prefixes: users allowed to slap us (empty = all nicks)
        read_attrs = ('accept_channels', 'accept_nick_prefixes')
        for read_attr in read_attrs:
            if read_attr in self.nv.keys():
                setattr(self, read_attr, self.nv[read_attr])
            else:
                setattr(self, read_attr, '')
                self.nv[read_attr] = ''
        self.accept_channels = ListStr(self.accept_channels)
        self.accept_nick_prefixes = ListStr(self.accept_nick_prefixes)
        # Filename for file containing actions
        self.datafile = self.GetSavePath() + '/actions.txt'
        self.reload_data_file()
        return znc.CONTINUE

    def reload_data_file(self):
        """Load pre-recorded actions from our text file"""
        if os.path.isfile(self.datafile):
            try:
                actfile = open(self.datafile, 'r')
                for line in actfile:
                    line = line.strip()
                    self.actlist.append(line)
                actfile.close()
                self.memos_loaded = True
            except Exception:
                self.PutModule('ERROR: failed loading actions')

    def update_lists_in_registry(self):
        """Sync ZNC moddata with our data structures"""
        self.nv['accept_channels'] = str(self.accept_channels)
        self.nv['accept_nick_prefixes'] = str(self.accept_nick_prefixes)

    def is_nick_allowed(self, nickname):
        """Check if given nickname is allowed to slap us"""
        # Allow all nicks that match a pre-defined user prefix
        # or allow any nick if no prefixes are defined
        allowed = False
        for prefix in self.accept_nick_prefixes:
            if nickname.find(prefix) == 0:
                allowed = True
                break
        return allowed or len(self.accept_nick_prefixes) == 0

    def is_chan_allowed(self, channel):
        """Check if we should monitor a given channel"""
        # Allow only channels pre-defined by user
        # or allow any channel if nothing is pre-defined
        allowed = channel in self.accept_channels
        return allowed or len(self.accept_channels) == 0

    def is_name_ok(self, name, channel=False):
        """Check if nick/channel name contains valid characters"""
        # Valid character set will probably change in the future
        #self.PutModule('called validity check: ' + name + ' ' + str(channel))
        if name == '':
            return False
        if channel and (name[0] != '#' or name == '#'):
            return False
        valid = True
        if channel:
            name = name[1:]
        for char in name:
            if char.isalnum():
                continue
            if char in '-_.':
                continue
            valid = False
            break
        return valid

    def OnChanAction(self, nick, channel, message):
        """Auto-executed by ZNC when there's an action on any channel""" 
        # Check if it's time to slap back
        if not self.memos_loaded:
            self.PutModule('WARNING: init not complete yet')
            return znc.CONTINUE
        my_nick = self.GetUser().GetNick()
        if not self.is_nick_allowed(nick.GetNick()):
            return znc.CONTINUE
        if not self.is_chan_allowed(channel.GetName()):
            return znc.CONTINUE
        if message.s.find(my_nick) >= 0:
            newmsg = message.s.replace(my_nick, ACTNICK).strip()
            # Previously unknown actions should be recorded
            # for future use
            if not newmsg in self.actlist:
                actfile = open(self.datafile, 'a')
                actfile.write(newmsg + '\n')
                actfile.close()
                self.actlist.append(newmsg)
            answer = random.choice(self.actlist).\
                    replace(ACTNICK, nick.GetNick())
            answer = 'PRIVMSG {} :\x01ACTION {}\x01'.\
                    format(channel.GetName(), answer)
            self.PutIRC(answer)
            self.PutUser(':{} {}'.format(my_nick, answer))
        return znc.CONTINUE

    def OnModCommand(self, command_full):
        """Auto-executed by ZNC when user sends a command to our module"""
        args = tuple(\
                (arg for arg in command_full.strip().split(' ') if arg != ''))
        if len(args) > 0:
            command = args[0]
        else:
            return znc.CONTINUE

        if command == 'help':
            self.PutModule(''.join((\
            'Accepted commands: get, nickadd, nickdel, ',
            'nickclear, chanadd, chandel, chanclear')))

        elif command == 'get':
            self.PutModule('Current settings:')
            for key, value in self.nv.items():
                self.PutModule('{}: {}'.format(key, repr(value)))

        elif command in ('nickadd', 'chanadd'):
            curlist = self.accept_nick_prefixes \
                    if command == 'nickadd' else self.accept_channels
            if len(args) == 2:
                if not args[1].lower() in tuple(map(str.lower, curlist)):
                    if self.is_name_ok(args[1], command=='chanadd'):
                        curlist.append(args[1])
                        self.update_lists_in_registry()
                        self.PutModule('Add successful')
        elif command in ('nickdel', 'chandel'):
            curlist = self.accept_nick_prefixes \
                    if command == 'nickdel' else self.accept_channels
            if len(args) == 2:
                if args[1].lower() in tuple(map(str.lower, curlist)):
                    curlist.remove(args[1])
                    self.update_lists_in_registry()
                    self.PutModule('Delete successful')
        elif command in ('nickclear', 'chanclear'):
            curlist = self.accept_nick_prefixes \
                if command == 'nickclear' else self.accept_channels
            curlist[:] = []
            self.update_lists_in_registry()
            self.PutModule('Cleared!')
        return znc.CONTINUE
