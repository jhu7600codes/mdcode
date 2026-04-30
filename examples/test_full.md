#import lib-mdcode
#import lib-autoVar

#print | === MDCode test file ===
#print | ...

#print | --- 1. basic print ---
#print | hello from MDCode!

#print | --- 2. env + var print ---
#env HOME > homeDir
#print | home dir is: + homeDir

#print | --- 3. os command ---
#os | uname -r > kernelVer
##print | kernel version: + kernelVer

#print | --- 4. math ---
#math | 6 * 7 > answer
##print | 6 * 7 = + answer

#print | --- 5. string concat ---
#env USER > userName
#print | hey + userName | , welcome to MDCode.

#print | --- 6. writeFile + readFile ---
#writeFile /tmp/mdcode_hello.txt > | MDCode wrote this file!
##print | writeLog
#readFile /tmp/mdcode_hello.txt > fileContents
##print | file says: + fileContents

#print | --- 7. getVar (missing var, logs to stderr) ---
#getVar thisVarDoesNotExist
##print | getVarLog

#print | --- 8. error handling ---
#readFile /tmp/this_does_not_exist.txt > nothing
##err | readFailed
####print | caught it: file was missing, no crash.

#print | --- 9. autoVar strVar passthrough ---
#os | echo autoVar works > autoTest
##print strVar

#print | --- 10. var (create) ---
#var greeting (create) | hello MDCode world
#print greeting

#print | --- 11. var (edit) ---
#var greeting (edit) | goodbye MDCode world
#print greeting

#print | --- 12. var (create) then concat ---
#var lang (create) | MDCode
#print | language is: + lang

#print | ...
#print | === all tests done ===
#exit | 0
