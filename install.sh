#!/usr/bin/env bash
function link_file {
    source="${PWD}/$1"
    target="${HOME}/${1/_/.}"

    if [ -e "${target}" ] && [ ! -L "${target}" ]; then
        mv $target $target.bak
    fi

    ln -sf ${source} ${target}
}

if [ "$1" = "vim" ]; then
    for i in _vim*
    do
       link_file $i
    done
else
    for i in _*
    do
        link_file $i
    done
fi

echo 'get ack on ubuntu'
echo 'sudo apt-get install ack-grep'
echo 'ln -s /usr/bin/ack-grep /usr/bin/ack' 

#git submodule sync
#git submodule init
#git submodule update
#git submodule foreach git pull origin master
#git submodule foreach git submodule init
#git submodule foreach git submodule update
# setup command-t
#cd _vim/bundle/command-t
#rake make
