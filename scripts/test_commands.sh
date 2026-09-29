#!/bin/sh
# Этап 4: команды ls, cd, pwd, cat, tac на разных VFS.
. "$(dirname "$0")/common.sh"
build_vfs deep
build_vfs multi

title "Стартовый скрипт этапа 4 на глубокой VFS"
emulate --vfs build/deep.zip --script startup/stage4.txt </dev/null

title "Скрытые, пустые и двоичные файлы (диалог из stdin)"
printf '%s\n' 'ls' 'ls -a' 'ls -l' 'cat empty.txt' 'cat -n notes.txt' \
    'tac notes.txt data.csv' 'cat logo.png' 'cd logo.png' 'exit' |
    emulate --vfs build/multi.zip

title "Команды в пустой VFS по умолчанию"
printf '%s\n' 'ls' 'ls -a' 'pwd' 'cd ..' 'cat motd' 'exit' | emulate
