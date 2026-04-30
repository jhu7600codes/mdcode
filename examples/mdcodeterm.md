#import lib-mdcode
#import lib-autoVar

#print | welcome to mdcodeterm, a terminal made by jhu and claude.
#print | type help for available commands.
#print | ...

#loop | 99
###var handled (create) | no
###input | $ > cmdVar

###if | cmdVar = echo
#####var handled (create) | yes
#####input | echo> > echoCmd
#####print echoCmd

###if | cmdVar = help
#####var handled (create) | yes
#####print | commands: echo, help, ls, clear, exit

###if | cmdVar = ls
#####var handled (create) | yes
#####print | ls: no files found in directory.

###if | cmdVar = exit
#####var handled (create) | yes
#####print | goodbye.
#####exit | 0

###if | handled = no
#####print | mdcodeterm: command not found: + cmdVar

#print | session limit reached. goodbye.
#exit | 0
