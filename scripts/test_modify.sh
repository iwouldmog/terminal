#!/bin/sh
# Этап 5: команды rm и touch; изменения только в памяти.
. "$(dirname "$0")/common.sh"
build_vfs deep
build_vfs multi
cp build/deep.zip build/deep.orig.zip

title "Стартовый скрипт этапа 5 на глубокой VFS"
emulate --vfs build/deep.zip --script startup/stage5.txt </dev/null

title "Проверка: ZIP-архив VFS не изменился"
if cmp -s build/deep.zip build/deep.orig.zip; then
    echo "build/deep.zip is unchanged"
else
    echo "build/deep.zip was modified!"
fi
printf '%s\n' 'ls /home/user/docs' 'ls /var/log' 'exit' |
    emulate --vfs build/deep.zip

title "Скрытые и двоичные файлы (диалог из stdin)"
printf '%s\n' 'ls -a' 'rm .profile logo.png' 'touch .new data.csv' \
    'ls -a' 'cat .new' 'rm -r motd notes.txt readme.txt' 'ls -la' \
    'exit' | emulate --vfs build/multi.zip

title "Изменение VFS по умолчанию (без архива)"
printf '%s\n' 'touch a b c' 'ls' 'rm b' 'ls -l' 'vfs-init' 'ls' 'exit' |
    emulate
