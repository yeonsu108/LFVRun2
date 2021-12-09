#!/bin/bash
if [ -z "$1" ]
then
    echo "No Input Argument"
else
    sys=norm
    mkdir -p plot_STLFV/$1/
    rm -rf plot_STLFV/$1/*
    cd $1
    for i in run2 16pre 16post 17 18
    #for i in run2
    do
        python ../drawhists.py -Y $i -SYS $sys
        python ../drawhists.py -Y $i -L -SYS $sys
    #    python ../drawhists.py -Y $i -S
    #    python ../drawhists.py -Y $i -L -S
    done
    mv plot* ../plot_STLFV/$1
    mv stackhist* ../plot_STLFV/$1
    cd ../
fi
