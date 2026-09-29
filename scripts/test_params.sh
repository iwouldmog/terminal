#!/bin/sh
# Этап 2: запуск эмулятора со всеми сочетаниями параметров.
. "$(dirname "$0")/common.sh"
build_vfs minimal
build_vfs multi

title "Без параметров: VFS по умолчанию, диалог из stdin"
printf 'ls\nexit\n' | emulate

title "Только --vfs: имя VFS в приглашении берётся из пути"
printf 'cd /\nexit 0\n' | emulate --vfs build/minimal.zip

title "Только --script: стартовый скрипт, затем диалог"
printf 'ls after-script\nexit 7\n' | emulate --script startup/stage2.txt

title "Оба параметра"
emulate --vfs build/multi.zip --script startup/stage2_exit.txt </dev/null

title "Оба параметра в форме --name=value и в другом порядке"
emulate --script=startup/stage2_exit.txt --vfs=build/minimal.zip </dev/null

title "Справка по параметрам"
emulate --help </dev/null
