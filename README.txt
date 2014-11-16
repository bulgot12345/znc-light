znc-light is a collection of ZNC scripts in Python (currently only one)
ZNC is an IRC bouncer (http://znc.in)

slap_ai.py: Answers back action when certain persons slap you on certain
channels.
Action database is self-growing. The answer is a random string from the
database with slapper's nickname substituted.
Known actions are stored in moddata/actions.txt
On first load, issue 'get' and 'help' commands to change default settings 
if desired.
