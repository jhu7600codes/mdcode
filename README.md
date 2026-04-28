#import lib-mdcode
#import lib-autoVar

#print | === welcome to mdcode ===

#var name (create) | mdcode
#print | this language is called: + name

#var version (create) | 1.0
#print | version: + version

#math | 1 + 1 > onePlusOne
#print | 1 + 1 = + onePlusOne

#math | 999 * 0 > nope
#print | 999 * 0 = + nope

#var mood (create) | alive
#print | interpreter is: + mood

#os | echo still running > statusVar
##print strVar

#var mood (edit) | maybe broken
#print | interpreter is now: + mood

#writeFile /tmp/readme_test.txt > | mdcode was here
#readFile /tmp/readme_test.txt > proof
#print | file proof: + proof

#readFile /tmp/this_does_not_exist_at_all.txt > ghost
##err | readFailed
####print | yeah that file doesnt exist lol

#env USER > who
#print | running as: + who

#env NONEXISTENT_VAR_123 > nothing
#print | nonexistent env: + nothing

#loop | 3
###print | looping…

#print | === done, if u see this it didnt crash ===
#exit | 0
