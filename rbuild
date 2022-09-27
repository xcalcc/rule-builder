#!/bin/bash


# ====================
# rbuild
# automation script for building
# rules given the fsm file and 
# dependencies
# ====================


# =========== CHECK SYSTEM REQUIREMENT =============

current=$(pwd) # where user resides in
tmp=`which rbuild`
target=`dirname $tmp`
$target/bin/checker


stat=$?
if test $stat -eq 2
then
    exit 0
fi

call_help(){
    # explain the command usage
    echo "Usage: rbuild <rule_file1> [...] [-j jar1:jar2:jar3] [-m mvn source project]"
    exit 0
}

# =========== CHECK INPUT ARGUMENT =============
rules=()  # containing filenames of rule file
n=1
for i in $@;
do
    if [ "${i:0:1}" == "-" ]; then
        break
    fi
    if [ ! -f $i ]; then
        echo "Error: $i not found"
        call_help
    fi

    rules+=($i)
    n=$((n+1))
done

if [ $n -eq 1 ];then
    call_help
fi

rule=${rules[0]}

shift $((n-1))
echo $@

# options parsing with getopts
while getopts ':j:m:' option;
do
    case $option in 
    j)
        JARSPATH=$OPTARG
        ;;
    m)
        MAVENPATH=$OPTARG
        ;;
    :)
        echo "$OPTARG requires argument"
        call_help
        ;;
    *)
        echo "Option $OPTARG not recognised"
        call_help
        ;;
    esac
done

# for jar files, check if exist, set main jar
if [ ! -z $JARSPATH ];then
    # take first argument as main_jar
    IFS=":" read -r -a JARS <<< $JARSPATH
    IFS=" "

    for i in ${JARS[@]}
    do
        if [ ! -f $i ]; then
            echo "Error: file $i not found"
            exit 0 
        fi        
    done
    main_jar=${JARS[0]}
else
    main_jar="rt.jar"  # just as a flag
fi

# Check for maven path
if [ ! -z $MAVENPATH ]; then
    if [ -f "$MAVENPATH/pom.xml" ]; then
        echo "Maven Project Found!"
    else
        echo "Error: $MAVENPATH is not a maven project"
    fi
fi


# =========== FILE INTERMEDIATE STORAGE =============
ERROR_NAME=`echo "$rule"|awk -F. '{print $1}'`
echo "Creating a sub-directotry for $ERROR_NAME"

if [ -d "$target/rules/$ERROR_NAME" ]; then
    echo "Rule $ERROR_NAME already exist"
    rm -r $target/rules/$ERROR_NAME/*
else
    mkdir "$target/rules/$ERROR_NAME"
fi

RULE_DIR="$target/rules/$ERROR_NAME" # sub-directory of the rule

mkdir "$RULE_DIR/rule/"
mkdir "$RULE_DIR/depn/"
mkdir "$RULE_DIR/scan/"

for jar in ${JARS[@]}
do
    echo "$jar being moved"
    cp $jar $RULE_DIR/depn/
done

if [ ! -z $MAVENPATH ]; then
    cd $MAVENPATH
    mvn package
    cp target/*.jar $RULE_DIR/depn
    main_jar=`find target/ -name '*.jar'`
    main_jar="`basename $main_jar`"
    cd $current # back to initial position
fi

# copy every rule file into the {rule}/ directory
for i in ${rules[@]}; do
    cp $i $RULE_DIR/rule
done


# =========== GENERATING RESOURCES =============

scripts=$target/lib
cd $RULE_DIR
$scripts/fsm_generate.py $RULE_DIR/rule/$rule
#$scripts/gen_fsm/fsm_generate.py $RULE_DIR/rule/$rule
#cp $RULE_DIR/rule/$rule $RULE_DIR/output/$rule.rule
for i in ${rules[@]}; do
    cp $RULE_DIR/rule/$i $RULE_DIR/output/$i.rule 
done

# =========== RULE COMPILATION =============
$scripts/compile.sh output/
cp output/user_def_rule.a scan/ # moved to scann
cd output
find . -type f ! -name '*.rule' -delete 
find . -type d ! -name '.' -delete


# =========== lib.o/rt.o dependency  =============
xvsa_dir=`which xvsa`
bin_dir=`dirname $xvsa_dir` 
mapfej_exc=$bin_dir/../lib/1.0/mapfej

echo "Main dependency is : $main_jar"

# TODO: Currently focuses on java project
if [ $main_jar == "rt.jar" ]; then
    # no need for further compilation, just get rt.o from lib
    echo "using rt.o"
else
    # need mapfej to help out
    cmd="$mapfej_exc -VTABLE=true"
    cd $RULE_DIR/depn
    for entry in ./*
    do
        name=`basename $entry`
        if [ "$main_jar" == "$name" ]; then
            cmd="$cmd -fC,$name"
        else
            cmd="$cmd -cp=$name"
            #cmd="$cmd -fC,$name"
        fi 
    done
    cmd="$cmd -fB,lib.o" # creating lib.o as dependency
    echo "$cmd"
    $cmd
    mv lib.o $RULE_DIR/scan # move to scan folder
    cd $RULE_DIR
fi



exit 0
