#!/bin/bash
find . -name '*.pyc' -delete

args=("$@")
num_args=${#args[@]}
index=0

with_coverage=false
extra=""

while [ "$index" -lt "$num_args" ]
do
    case "${args[$index]}" in
        "-c"|"--coverage")
            with_coverage=true
            ;;
        "-f"|"--failfast")
            extra="$extra --failfast"
            ;;
    esac
    let "index = $index + 1"
done

cd testproject

if [ $with_coverage == true ]; then
    coverage run manage.py test nani $extra
    statuscode=$?
    coverage html
    if which x-www-browser &> /dev/null; then 
        x-www-browser htmlcov/index.html
    else
        open htmlcov/index.html
    fi
else
    python manage.py test nani $extra
    statuscode=$?
fi
cd ..
exit $statuscode
